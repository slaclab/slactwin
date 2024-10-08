"""Wrapper to run slactwin simulations from the command line.

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template import template_common
import asyncio
import pykern.pkio
import slactwin.template.slactwin


def run_background(cfg_dir):
    """Run a multicore/long running simulation.

    Args:
      cfg_dir (str): The directory to run in.
    """

    async def _runLive(params):
        o = cfg_dir.join(slactwin.template.slactwin.LIVE_OUT)
        c = slactwin.db_api_client.for_job_cmd()
        q = PKDict(
            twin_name=params.twinModel,
            machine_name=params.accelerator,
            run_summary_id=None,
        )
        while True:
            try:
                q.pkupdate(await c.call_api("live_monitor", q))
            except tornado.simple_httpclient.HTTPTimeoutError:
                continue
            pykern.pkio.atomic_write(
                o,
                pykern.pkjson.dump_bytes(PKDict(runSummaryId=q.run_summary_id)),
            )

    cfg_dir = pykern.pkio.py_path(cfg_dir)
    if cfg_dir.join(template_common.PARAMETERS_PYTHON_FILE).exists():
        # must be live so this throws here
        asyncio.run(
            _runLive(template_common.exec_parameters().searchSettings),
        )
