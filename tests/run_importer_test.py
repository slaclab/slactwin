"""Test run_importer

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""


def test_parse():
    from slactwin import quest

    with quest.import_and_start() as qcall:
        from pykern import pkunit, pkio
        from pykern.pkdebug import pkdp
        from slactwin import run_importer

        for d in pkunit.case_dirs():
            for f in pkio.sorted_glob("summary/*/*/*/*.json"):
                e = _setup_data(f, d)
                run_importer.insert_run_summary(f, qcall=qcall)
                qcall.db.commit()
                r = qcall.db.select_one("RunSummary", summary_path=str(e.summary_path))
                pkunit.pkeq(e.snapshot_dt, r.snapshot_end)
                pkunit.pkeq(e.snapshot_path, str(r.snapshot_path))
                v = qcall.db.query(
                    "run_value",
                    run_summary_id=r.run_summary_id,
                    tag="pv",
                    base="QUAD:HTR:460:BACT",
                )
                pkunit.pkeq(-3.0283967275626105, v)
                v = qcall.db.query(
                    "run_value",
                    run_summary_id=r.run_summary_id,
                    tag="impact",
                    base="end_norm_emit_4d",
                )
                pkunit.pkeq(4.592702508485681e-13, v)


def _setup_data(summary, case_dir):
    from pykern import pkjson, pkio
    from pykern.pkcollections import PKDict
    import datetime

    def _snapshot_path():
        return pkio.sorted_glob(
            str(summary.dirpath().join("*")).replace("/summary/", "/snapshot/")
        )[0]

    summary.write(summary.read().replace("CASE_DIR", str(case_dir)))
    j = pkjson.load_any(summary)
    rv = PKDict(
        snapshot_path=_snapshot_path(),
        snapshot_dt=datetime.datetime.fromisoformat(j.isotime)
        .astimezone()
        .replace(tzinfo=None),
        summary_path=summary,
    )
    rv.snapshot_path.setmtime(rv.snapshot_dt.timestamp())
    return rv
