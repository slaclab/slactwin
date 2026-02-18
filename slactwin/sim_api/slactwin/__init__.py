"""api for slactwin

:copyright: Copyright (c) 2025 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import datetime
import sirepo.quest
import sirepo.sim_data
import sirepo.simulation_db

_SIM_DATA, SIM_TYPE, _ = sirepo.sim_data.template_globals(sim_type="slactwin")


def init_apis(**kwargs):
    pass


_SIM_TYPE_FOR_TWIN_NAME = PKDict(
    impact="impactt",
)


class API(sirepo.quest.API):

    @sirepo.quest.Spec("require_plan")
    async def api_slactwinSimFromRunSummary(self):
        d = self.parse_post(type=SIM_TYPE).req_data
        d.targetSimType = _SIM_TYPE_FOR_TWIN_NAME.get(d.twinName, d.twinName)
        # ensure impact-t exists for the user
        sirepo.simulation_db.simulation_dir(d.targetSimType, qcall=self)
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

    @sirepo.quest.Spec("require_plan")
    async def api_slactwinListMachines(self):
        """Returns a map of all machine_name, twin_name to simulationId"""

        def _create_new_sim(name, machine_name, twin_name):
            d = sirepo.simulation_db.default_data(SIM_TYPE)
            d.models.simulation.pkupdate(
                name=name,
                machine_name=machine_name,
                twin_name=twin_name,
                elementPosition="absolute" if "impact" in twin_name else "relative",
            )
            d.models.searchSettings.pkupdate(
                machine_name=machine_name,
                twin_name=twin_name,
                searchStartTime=_delta_now(-365),
                searchStopTime=_delta_now(365),
            )
            sirepo.simulation_db.save_new_simulation(d, qcall=self)
            return d.models.simulation.simulationId

        def _delta_now(delta_days):
            return (
                (datetime.datetime.now() + datetime.timedelta(days=delta_days))
                .replace(second=0, microsecond=0)
                .timestamp()
            )

        async def _query_run_kinds():
            return (
                (
                    await self.call_api(
                        "statelessCompute",
                        body=PKDict(
                            method="db_api",
                            args=PKDict(
                                api_name="run_kinds",
                                api_args=PKDict(),
                            ),
                            simulationType=SIM_TYPE,
                        ),
                    )
                )
                .content_as_object()
                .run_kinds
            )

        async def _sim_ids_by_name():
            return PKDict(
                [
                    (_sim_name(v.simulation), v.simulationId)
                    for v in (
                        await self.call_api(
                            "listSimulations",
                            body=PKDict(
                                simulationType=SIM_TYPE,
                            ),
                        )
                    ).content_as_object()
                ]
            )

        def _sim_name(m):
            if "machine_name" not in m:
                return None
            return f"{m.machine_name} {m.twin_name}"

        s = await _sim_ids_by_name()
        if "error" in s:
            return s

        res = []
        for r in await _query_run_kinds():
            # add any missing (machine_name, twin_name) sims
            n = _sim_name(r)
            sid = s.get(n)
            if not sid:
                sid = _create_new_sim(n, r.machine_name, r.twin_name)
            r.simulationId = sid
            res.append(r)
        return PKDict(run_kinds=res)
