"""Import lume-impact-live-demo files manually or automatically

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import asyncio
import datetime
import dateutil
import pykern.pkconfig
import pykern.pkio
import pykern.pkjson
import pykern.util
import re
import slactwin.config
import slactwin.const
import watchdog.events
import watchdog.observers

_SUMMARY_PATH_RE = re.compile(
    r"(.*)/summary/(\d{4}/\d\d/\d\d/).+-(\w+)-\d{4}-\d\d-\d\dT"
)


def init_module(loop):
    global _cfg

    @pykern.pkconfig.parse_none
    def _path(value):
        if value is not None:
            return pykern.util.cfg_absolute_dir(value)
        return slactwin.config.dev_path("summary").ensure(dir=True, ensure=True)

    _cfg = pykern.pkconfig.init(
        summary_dir=pykern.pkconfig.RequiredUnlessDev(
            None,
            _path,
            "where the summary files can be found",
        ),
    )
    _Watcher(loop)


def insert_run_summary(path, qcall):
    _Parser(
        summary=pykern.pkjson.load_any(path), summary_path=path, qcall=qcall
    ).create()


class _Parser(PKDict):

    # save inputs and outputs in some type of row tag model
    # row ids are returned in searching
    def create(self):
        v = self._summary_values(self.summary)
        self._run_values_create(
            self.qcall.db.insert("RunSummary", **v).run_summary_id,
            v.run_kind_id,
        )

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
                self.qcall.db.insert(
                    "RunValueFloat",
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
                self._run_value_names = self.qcall.db.column_map(
                    "RunValueName",
                    key_col="name",
                    value_col="run_value_name_id",
                    run_kind_id=run_kind_id,
                )
            if rv := self._run_value_names.get(name):
                return rv
            self._run_value_names[name] = self.qcall.db.insert(
                "RunValueName",
                name=name,
                run_kind_id=run_kind_id,
            ).run_value_name_id
            return self._run_value_names[name]

        _create_one("impact", self.summary.outputs.items())
        _create_one("pv", self._pv_items())

    def _pv_items(self):
        s = set()
        for i, n in self.summary.pv_mapping_dataframe.device_pv_name.items():
            if n not in s:
                s.add(n)
                yield n, self.summary.pv_mapping_dataframe.pv_value[i]

    def _run_kind(self, machine):
        def _id(name):
            return self.qcall.db.select_or_insert(
                "RunKind", machine_name=machine, twin_name=name
            ).run_kind_id

        if "impact_config" in self.summary.config:
            n = "impact"
        else:
            raise ValueError(
                f"unable to determine simulation type config={self.summary.config}"
            )
        return PKDict(run_kind_id=_id(n))

    def _snapshot(self, root, dt_dir):
        p = f"{root}/snapshot/{dt_dir}*{self.summary.isotime}.h5"
        if not (f := pykern.pkio.sorted_glob(p)):
            raise ValueError(f"no snapshot found for glob={p}")
        if len(f) > 1:
            raise ValueError(f"too many snapshots matching glob={p} matches={f}")
        return PKDict(
            snapshot_end=datetime.datetime.fromtimestamp(int(f[0].mtime())),
            snapshot_path=str(f[0]),
        )

    def _summary_values(self, summary):
        # summary/yyyy/mm/dd
        if not (m := _SUMMARY_PATH_RE.search(str(self.summary_path))):
            raise ValueError(
                f"summary path={self.summary_path} does not match regex={_SUMMARY_PATH_RE}"
            )
        return (
            self._run_kind(m.group(3))
            .pkupdate(
                self._snapshot(m.group(1), m.group(2)),
            )
            .pkupdate(
                archive_path=self.summary.outputs.archive,
                run_end=self._run_end(),
                summary_path=str(self.summary_path),
            )
        )

    def _run_end(self):
        return (
            dateutil.parser.isoparse(self.summary.isotime)
            .astimezone()
            .replace(tzinfo=None)
        )


class _Watcher(watchdog.events.FileSystemEventHandler):
    def __init__(self, loop):
        super().__init__()
        self.__loop = loop
        self.__queue = asyncio.Queue()
        self.__loop.call_soon_threadsafe(self.__process)
        o = watchdog.observers.Observer()
        o.schedule(self, str(_cfg.summary_dir), recursive=True)
        o.start()

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".json"):
            self.__loop.call_soon_threadsafe(self.__queue.put_nowait, event)

    async def __process(self):
        async for e in self.__queue:
            try:
                with sirepo.quest.start() as qcall:
                    insert_run_summary(e.src_path, qcall)
            finally:
                self.__queue.task_done()
