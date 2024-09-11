"""Database server API

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import datetime
import slactwin.db
import slactwin.quest


class DbAPI(slactwin.quest.API):
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

        try:
            # TODO(robnagler) generalize
            if x := api_args.get("min_max_values"):
                if "snapshot_end" in x:
                    x.snapshot_end = PKDict(
                        {k: _dt(v) for k, v in x.snapshot_end.items()}
                    )
            return self.db.query(api_name, **api_args)
        except slactwin.db.BaseExc as e:
            raise e.as_api_error()
