"""test queries

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""


def test_run_kinds():
    from pykern import pkunit, pkio
    from pykern.pkdebug import pkdp, pkdpretty
    from slactwin import quest, const

    pkunit.data_dir().join(const.DEV_DB_BASENAME).copy(pkunit.work_dir())
    with quest.import_and_start() as qcall:
        a = qcall.db.query("run_kinds_and_value_names")
        pkunit.pkeq(["sc_inj"], list(a.machines.keys()))
        pkunit.pkeq(["impact"], list(a.machines.sc_inj.twins.keys()))
        pkunit.pkeq(
            "impact^end_cov_x__px",
            a.machines.sc_inj.twins.impact.run_value_names[0],
        )


def test_runs_by_date():
    from pykern import pkunit, pkio
    from pykern.pkdebug import pkdp, pkdpretty
    from slactwin import quest, const
    from pykern.pkcollections import PKDict
    import datetime

    pkunit.data_dir().join(const.DEV_DB_BASENAME).copy(pkunit.work_dir())
    with quest.import_and_start() as qcall:
        a = qcall.db.query(
            "runs_by_date_and_values",
            machine_name="sc_inj",
            twin_name="impact",
            min_max_values=PKDict(
                {
                    "snapshot_end": PKDict(
                        # misses 2024-06-19 14:03:29.000000
                        max=datetime.datetime.fromisoformat("2024-06-19T14:03:28"),
                        # gets 2024-06-19 13:42:21.000000
                        min=datetime.datetime.fromisoformat("2024-06-19T13:42:21"),
                    ),
                    # excludes 2024-06-19 13:47:38.000000|63.119275042593
                    "impact^end_cov_x__px": PKDict(min=65),
                }
            ),
            additional_run_values=["pv^SOLN:GUNB:212:BACT"],
        )
        pkunit.pkeq(3, len(a.rows))
        pkunit.pkeq("2024-06-19T13:42:21", a.rows[0].snapshot_end.isoformat())
        pkunit.pkeq("2024-06-19T13:58:07", a.rows[-1].snapshot_end.isoformat())
        for r in a.rows:
            pkunit.pkok(
                r.run_values["impact^end_cov_x__px"] >= 65, "value < 65 row={}", r
            )
        pkunit.pkeq(0.044200997724189985, a.rows[0].run_values["pv^SOLN:GUNB:212:BACT"])
