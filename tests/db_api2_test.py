"""Test stateless_compute_db_api

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

import contextlib


# TODO(robnagler) share
def setup_module(module):
    import os
    from pykern import util

    p = str(util.unbound_localhost_tcp_port(10000, 11000))
    os.environ.update(
        PYKERN_PKDEBUG_WANT_PID_TIME="1",
        SLACTWIN_CONFIG_DB_API_TCP_PORT=p,
        SLACTWIN_GLOBAL_RESOURCES_SLACTWIN_DB_API_TCP_PORT=p,
    )


def test_slactwin_stateless_compute(fc):
    from slactwin import const
    from pykern import pkunit

    pkunit.data_dir().join(const.DEV_DB_BASENAME).copy(pkunit.work_dir())
    with _server():
        from pykern import pkunit, pkdebug
        from pykern.pkcollections import PKDict

        r = _do(fc, "run_kinds_and_values", PKDict())
        pkunit.pkeq(["sc_inj"], list(r.machines.keys()))


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

    def _child():
        from pykern import pkdebug

        try:
            from slactwin.pkcli import service
            from slactwin import config, modules

            modules.import_and_init()
            service.Commands().db()
        except Exception as e:
            pkdebug.pkdlog("server exception={} stack={}", e, pkdebug.pkdexc())
        finally:
            os._exit(0)

    p = os.fork()
    if p == 0:
        _child()
    try:
        time.sleep(1)
        yield None

    finally:
        os.kill(p, signal.SIGKILL)
