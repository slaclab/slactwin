"""test db api

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

import pytest
import contextlib


@pytest.mark.asyncio
async def test_run_all():
    from slactwin import const, modules
    from pykern.pkcollections import PKDict
    import datetime

    with _server():
        from slactwin import config, db_api_client
        from pykern import pkunit
        from pykern import pkdebug

        pkunit.data_dir().join(const.DEV_DB_BASENAME).copy(pkunit.work_dir())
        modules.import_and_init()
        c = db_api_client.DbAPIClient()
        r = await c.post("run_kinds_and_values", PKDict())
        pkunit.pkeq(
            "impact^end_cov_x__px",
            r.machines.sc_inj.twins.impact.run_values[0],
        )
        t = int(datetime.datetime.fromisoformat("2024-06-19T13:42:21").timestamp())
        r = await c.post(
            "runs_by_date_and_values",
            PKDict(
                machine_name="sc_inj",
                twin_name="impact",
                min_max_values=PKDict(
                    {
                        "snapshot_end": PKDict(
                            # misses 2024-06-19 14:03:29.000000
                            max=int(
                                datetime.datetime.fromisoformat(
                                    "2024-06-19T14:03:28"
                                ).timestamp()
                            ),
                            # gets 2024-06-19 13:42:21.000000
                            min=t,
                        ),
                        # excludes 2024-06-19 13:47:38.000000|63.119275042593
                        "impact^end_cov_x__px": PKDict(min=65),
                    }
                ),
                additional_run_values=["pv^SOLN:GUNB:212:BACT"],
            ),
        )
        # Since the db is committed, this is a fixed value
        pkunit.pkeq(35002, r.rows[0].run_summary_id)
        pkunit.pkeq(3, len(r.rows))
        pkunit.pkeq(t, r.rows[0].snapshot_end)


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

    return str(pkunit.unbound_localhost_tcp_port(10000, 11000))
