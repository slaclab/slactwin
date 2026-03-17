"""Import archive files manually or automatically

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import asyncio
import datetime
import dateutil
import pykern.pkconfig
import pykern.pkio
import pykern.util
import re
import slactwin.config
import slactwin.const
import slactwin.util
import watchdog.events
import watchdog.observers.polling

_ARCHIVE_PATH_RE = re.compile(
    r"(.*)/archive/(\d{4}/\d\d/\d\d/).+-(\w+)-\d{4}-\d\d-\d\dT"
)

_cfg = None

_notifier = None


def cfg():
    global _cfg
    if not _cfg:
        _cfg = pykern.pkconfig.init(
            archive_dir=pykern.pkconfig.RequiredUnlessDev(
                None,
                _archive_dir,
                "where the archive files can be found",
            ),
        )
    return _cfg


def insert_run_summary(path, qcall):
    return _Parser(archive_path=pykern.pkio.py_path(path), qcall=qcall).create()


async def next_summary(machine_name, twin_name, run_summary_id, qcall):
    def _run_kind_id():
        return qcall.db.query(
            "run_kind_by_names",
            machine_name=machine_name,
            twin_name=twin_name,
        ).run_kind_id

    return PKDict(
        run_summary_id=await _notifier.next_id(_run_kind_id(), run_summary_id, qcall),
    )


async def start_notifier():
    global _notifier

    if _notifier:
        raise AssertionError("may only be called once")
    _notifier = _SummaryNotifier()


class _Parser(PKDict):

    # save inputs and outputs in some type of row tag model
    # row ids are returned in searching
    def create(self):
        """Inserts run_summary and associated records
        Returns:
            PKDict: run_summary record or None if it exists
        """
        if self.qcall.db.query(
            "archive_path_exists", archive_path=str(self.archive_path)
        ):
            return None
        self.summary = slactwin.util.summary_from_archive(self.archive_path)
        rv = self.qcall.db.session().insert(
            "run_summary", self._summary_values(self.summary)
        )
        self._run_values_create(rv.run_summary_id, rv.run_kind_id)
        self.qcall.db.commit()
        return rv

    def _run_values_create(self, run_summary_id, run_kind_id):
        def _create(name, value):
            if "_run_values_seen" not in self:
                self._run_values_seen = set()
            elif name in self._run_values_seen:
                return
            self._run_values_seen.add(name)
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                or value is None
            ):
                self.qcall.db.session().insert(
                    "run_value_float",
                    run_summary_id=run_summary_id,
                    run_value_name_id=_name_id(name),
                    value=value,
                )

        def _create_one(tag, items):
            if tag not in slactwin.const.RUN_VALUE_TAGS:
                raise AssertionError(
                    f"invalid tag={tag} RUN_VALUE_TAGS={slactwin.const.RUN_VALUE_TAGS}"
                )
            k = tag + slactwin.const.RUN_VALUE_SEP
            for n, v in items:
                _create(k + n, v)

        def _name_id(name):
            if "_run_value_names" not in self:
                self._run_value_names = self.qcall.db.session().column_map(
                    "run_value_name",
                    key_col="name",
                    value_col="run_value_name_id",
                    where=PKDict(run_kind_id=run_kind_id),
                )
            if rv := self._run_value_names.get(name):
                return rv
            self._run_value_names[name] = (
                self.qcall.db.session()
                .insert(
                    "run_value_name",
                    name=name,
                    run_kind_id=run_kind_id,
                )
                .run_value_name_id
            )
            return self._run_value_names[name]

        _create_one("outputs", self.summary.outputs.items())
        _create_one("pv", self._pv_items())

    def _pv_items(self):
        for i, r in self.summary.pv_mapping_dataframe.iterrows():
            yield r["device_pv_name"], r["pv_value"]

    def _run_kind(self, machine):
        def _id(name):
            return (
                self.qcall.db.session()
                .select_or_insert("run_kind", machine_name=machine, twin_name=name)
                .run_kind_id
            )

        return PKDict(run_kind_id=_id(self.summary.twin_name))

    def _summary_values(self, summary):
        # archive/yyyy/mm/dd
        if not (m := _ARCHIVE_PATH_RE.search(str(self.archive_path))):
            raise ValueError(
                f"archive path={self.archive_path} does not match regex={_ARCHIVE_PATH_RE}"
            )
        return self._run_kind(m.group(3)).pkupdate(
            snapshot_end=datetime.datetime.fromisoformat(self.summary.isotime)
            .astimezone()
            .replace(tzinfo=None),
            archive_path=str(self.archive_path),
        )


class _SummaryNotifier:
    """Keeps db up to date with new summaries and notifies clients of updates"""

    def __init__(self):
        self._archive_dir = cfg().archive_dir
        self._queue = asyncio.Queue()
        l = asyncio.get_running_loop()
        self._watcher = _SummaryWatcher(l, self._queue, self._archive_dir)
        self._run_kinds = PKDict()
        l.create_task(self._process())

    async def next_id(self, run_kind_id, curr_id, qcall):
        def _get_max():
            if not (v := self._run_kinds.get(run_kind_id)):
                r = qcall.db.query("max_run_summary", run_kind_id=run_kind_id)
                self._run_kinds[run_kind_id] = PKDict(
                    max_id=r.run_summary_id, clients=[]
                )
                return r.run_summary_id
            if v.max_id != curr_id:
                return v.max_id
            return None

        if rv := _get_max():
            return rv
        q = asyncio.Queue(1)
        self._run_kinds[run_kind_id].clients.append(q)
        rv = await q.get()
        q.task_done()
        return rv

    async def _process(self):
        """Make db consistent with files, await new summaries, and notify clients"""

        async def _init():
            """Insert runs into db that are already on disk but do not yet exist"""
            from slactwin.pkcli import db

            await asyncio.sleep(1)
            db.Commands().insert_runs(self._archive_dir)

        def _notify(new_run):
            """Notify any next_summary clients"""
            if not new_run or not (v := self._run_kinds.get(new_run.run_kind_id)):
                return
            # POSIT: old runs must not be inserted after the watcher starts
            v.max_id = new_run.run_summary_id
            for q in v.clients:
                q.put_nowait(v.max_id)
            v.clients = []

        await _init()
        while True:
            p = await self._queue.get()
            try:
                with slactwin.quest.start() as qcall:
                    _notify(insert_run_summary(p, qcall))
            except Exception as e:
                pkdlog("IGNORING exception={} path={} stack={}", e, p, pkdexc())
            finally:
                self._queue.task_done()


class _SummaryWatcher(watchdog.events.FileSystemEventHandler):
    def __init__(self, loop, queue, archive_dir):
        super().__init__()
        # Must be called from the main thread
        self.__loop = loop
        self.__queue = queue
        # TODO(robnagler) may need to optimize for size
        self.__seen = set()
        o = watchdog.observers.polling.PollingObserver()
        o.schedule(self, str(archive_dir), recursive=True)
        o.start()

    # On moved, called when file moved within the archive directory (from pkcli.mock)
    def on_moved(self, event):
        # Different thread so must share same loop as __process
        self._handle_new_file(event, "moved", "dest_path")

    # When a file is moved into the archive directory
    def on_created(self, event):
        # Different thread so must share same loop as __process
        self._handle_new_file(event, "created", "src_path")

    def _handle_new_file(self, event, event_type, path_name):
        path = getattr(event, path_name, None)
        if (
            path
            and not event.is_directory
            and event.event_type == event_type
            and path.endswith(".h5")
            and path not in self.__seen
        ):
            self.__seen.add(path)
            self.__loop.call_soon_threadsafe(self.__queue.put_nowait, path)


@pykern.pkconfig.parse_none
def _archive_dir(value):
    if value is not None:
        return pykern.util.cfg_absolute_dir(value)
    # Needs to exist, because _SummaryWatcher checks it
    return slactwin.config.dev_path("archive").ensure(dir=True)
