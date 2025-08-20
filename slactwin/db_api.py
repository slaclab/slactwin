"""Database server API implementation

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import contextlib
import datetime
import pykern.sql_db
import slactwin.db
import slactwin.quest
import slactwin.run_importer


class DbAPI(slactwin.quest.API):
    """API entry points to be dispatched

    All entry points take ``api_args``, which is a dictionary of arguments.

    DateTimes should be passed in api_args as an int of seconds from the Unix epoch.

    Entry points return:

    api_result
        typically a dictionary, but could be an any Python data structure
    api_error
        is None on success. Otherwise, contains an string describing the error.
    """

    async def api_live_monitor(self, api_args):
        with _raise_on_error():
            return await slactwin.run_importer.next_summary(qcall=self, **api_args)

    async def api_run_kinds_and_values(self, api_args):
        return await self.__query("run_kinds_and_values", api_args)

    async def api_run_summary_by_id(self, api_args):
        return await self.__query("run_summary_by_id", api_args)

    async def api_runs_by_date_and_values(self, api_args):
        return await self.__query("runs_by_date_and_values", api_args)

    async def __query(self, api_name, api_args):
        def _dt(value):
            return value if value is None else datetime.datetime.fromtimestamp(value)

        def _fix_row(row):
            for i, c in enumerate(row):
                if hasattr(c, "timestamp") and callable(c.timestamp):
                    row[i] = int(c.timestamp())

        with _raise_on_error():
            # TODO(robnagler) generalize
            if x := api_args.get("min_max_values"):
                if "snapshot_end" in x:
                    x.snapshot_end = PKDict(
                        {k: _dt(v) for k, v in x.snapshot_end.items()}
                    )
            return self.db.query(api_name, **api_args)


@contextlib.contextmanager
def _raise_on_error():
    try:
        yield
    except pykern.sql_db.BaseExc as e:
        raise e.as_api_error()
