"""api for slactwin

:copyright: Copyright (c) 2025 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import sirepo.quest
import sirepo.sim_data
import sirepo.simulation_db

_SIM_DATA, SIM_TYPE, _ = sirepo.sim_data.template_globals(sim_type="slactwin")


def init_apis(**kwargs):
    pass


class API(sirepo.quest.API):

    @sirepo.quest.Spec("require_plan")
    async def api_slactwinSimFromRunSummary(self):
        d = self.parse_post(type=SIM_TYPE).req_data
        # ensure impact-t exists for the user
        sirepo.simulation_db.simulation_dir("impactt", qcall=self)
        r = (
            await self.call_api(
                "statefulCompute",
                body=PKDict(
                    method="create_sim_for_run_summary",
                    args=d,
                    simulationType=SIM_TYPE,
                ),
            )
        ).content_as_object()
        if "sim_data" in r:
            s = sirepo.simulation_db.save_new_simulation(r.sim_data, qcall=self)
            return PKDict(
                simulationType=s.simulationType,
                simulation=s.models.simulation,
            )
        return r
