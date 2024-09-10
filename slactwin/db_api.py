"""database service

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import datetime
import slactwin.quest


class DbAPI(slactwin.quest.API):
    async def api_run_kinds_and_value_names(self, api_arg):
        return self.db.query("run_kinds_and_value_names", **api_arg)

    async def api_runs_by_date_and_values(self, api_arg):
        if x := api_arg.min_max_values.get("snapshot_end"):
            api_arg.min_max_values.snapshot_end = PKDict(
                {k: datetime.datetime.fromtimestamp(v) for k, v in x.items()}
            )
        rv = self.db.query("runs_by_date_and_values", **api_arg)
        for r in rv.rows:
            r.snapshot_end = int(r.snapshot_end.timestamp())
        return rv
