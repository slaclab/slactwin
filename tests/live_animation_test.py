"""Test stateless_compute_db_api

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

import contextlib


def test_slactwin_stateless_compute(fc):
    from slactwin import const
    from pykern import pkunit

    pkunit.data_dir().join(const.DEV_DB_BASENAME).copy(pkunit.work_dir())
    with _server():
        from pykern import pkunit, pkdebug
        from pykern.pkcollections import PKDict
        import time

        fc.sr_sim_type_set("slactwin")
        d = PKDict(name="new1", folder="/", simulationType=fc.sr_sim_type)
        d = fc.sr_post("newSimulation", d)
        pkdebug.pkdlog(d)
        d.models.liveAnimation = PKDict(accelerator="sc_inj", twinModel="impact")
        r = fc.sr_post(
            "runSimulation",
            PKDict(
                models=d.models,
                report="liveAnimation",
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            ),
        )
        pkdebug.pkdlog(r)
        # pkunit.pkok("outputInfo" not in r
        time.sleep(100)
        r = fc.sr_post("runStatus", r.nextRequest)
        pkdebug.pkdlog(r)
        assert 0


def _do(fc, api_name, api_args):
    from pykern.pkcollections import PKDict

    return fc.sr_post(
        "statelessCompute",
        PKDict(
            simulationType=fc.sr_sim_type,
            method="db_api",
            args=PKDict(api_name=api_name, api_args=api_args),
        ),
    )


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
