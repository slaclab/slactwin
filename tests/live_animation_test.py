"""Test liveAnimation simulation

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

import contextlib
import pytest

_NEW_SUMMARY_FILE = "lume-impact-live-demo-s3df-sc_inj-2024-06-19T07:03:29-07:00.json"


@pytest.mark.asyncio
async def test_slactwin_live_animation(fc):
    from pykern import pkunit
    from slactwin import const

    pkunit.data_dir().join(const.DEV_DB_BASENAME).copy(pkunit.work_dir())
    with _server():
        from pykern import pkunit, pkdebug, pkio
        from pykern.pkcollections import PKDict
        import asyncio, shutil
        from slactwin import run_importer

        d = fc.sr_sim_data("SLAC Digital Twin Database", sim_type=fc.sr_sim_type)
        d.models.searchSettings.pkupdate(
            accelerator="sc_inj",
            twinModel="impact",
            isLive="1",
        )
        r = fc.sr_post(
            "runSimulation",
            PKDict(
                models=d.models,
                report="animation",
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            ),
        )
        i = None
        for _ in range(10):
            await asyncio.sleep(r.nextRequestSeconds)
            r = fc.sr_post("runStatus", r.nextRequest)
            if i := r.pkunchecked_nested_get("outputInfo.runSummaryId"):
                break
        else:
            pkunit.pkfail("failed to get runSummaryId: runStatus={}", r)
        for s in pkio.sorted_glob(pkunit.data_dir().join("record1", "*")):
            shutil.copytree(
                str(s),
                str(run_importer.cfg().summary_dir.new(basename=s.basename)),
                # summary_dir exists even though it is empty
                dirs_exist_ok=True,
            )
        for _ in range(10):
            await asyncio.sleep(r.nextRequestSeconds)
            r = fc.sr_post("runStatus", r.nextRequest)
            if i != r.outputInfo.runSummaryId:
                return
        pkunit.pkfail("runSummaryId={} did not change: runStatus={}", i, r)


@contextlib.contextmanager
def _server():
    from pykern.pkcollections import PKDict
    import os, signal, time

    port = _port()
    import os

    c = PKDict(
        PYKERN_PKDEBUG_WANT_PID_TIME="1",
        SLACTWIN_CONFIG_DB_API_TCP_PORT=port,
    )
    os.environ.update(**c)
    from pykern import pkconfig

    pkconfig.reset_state_for_testing(c)
    from pykern import pkdebug

    p = os.fork()
    if p == 0:
        try:
            pkdebug.pkdlog("start server")
            from slactwin.pkcli import service
            from slactwin import config, modules

            modules.import_and_init()
            service.Commands().db()
        except Exception as e:
            pkdebug.pkdlog("server exception={} stack={}", e, pkdebug.pkdexc())
        finally:
            os._exit(0)
    try:
        time.sleep(1)
        yield None

    finally:
        os.kill(p, signal.SIGKILL)


def _port():
    from pykern import pkunit

    # TODO(robnagler) need to pass this through to agent
    return "9020"
    return str(pkunit.unbound_localhost_tcp_port(10000, 11000))
