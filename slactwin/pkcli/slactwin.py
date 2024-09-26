"""Wrapper to run slactwin simulations from the command line.

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from sirepo.template import template_common
import pykern.pkio
import slactwin.template.slactwin


def run_background(cfg_dir):
    """Run a multicore/long running simulation.

    Args:
      cfg_dir (str): The directory to run in.
    """

    async def _liveAnimation(params):
        o = cfg_dir.join(slactwin.template.slactwin.LIVE_ANIMATION_OUT)
        c = slactwin.db_api_client.for_job_cmd()
        q = PKDict(
            twin_name=params.liveAnimation.twinModel,
            machine_name=params.liveAnimation.accelerator,
            run_summary_id=None,
        )
        while True:
            q.pkupdate(await c.post("live_monitor", q))
            pykern.pkio.atomic_write(
                o,
                pykern.pkjson.dump_bytes(PKDict(runSummaryId=q.run_summary_id)),
            )

    cfg_dir = pykern.pkio.py_path(cfg_dir)
    if cfg_dir.join(template_common.PARAMETERS_PYTHON_FILE).exists():
        # must be liveAnimation so this throws here
        asyncio.run(_liveAnimation, template_common.exec_parameters().liveAnimation)
