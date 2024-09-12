"""test queries

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""


class Test:
    @classmethod
    def setup_class(cls):
        from pykern import pkunit, pkdebug
        from slactwin import quest, const
        from pykern.pkcollections import PKDict
        import datetime

        pkunit.data_dir().join(const.DEV_DB_BASENAME).copy(pkunit.work_dir())
        cls.PKDict = staticmethod(PKDict)
        cls.datetime = datetime
        cls.pkdebug = pkdebug
        cls.pkdp = staticmethod(pkdebug.pkdp)
        cls.pkdppretty = staticmethod(pkdebug.pkdppretty)
        cls.pkeq = staticmethod(pkunit.pkeq)
        cls.pkok = staticmethod(pkunit.pkok)
        cls.pkre = staticmethod(pkunit.pkre)
        cls.pkunit = pkunit
        cls.quest = quest
        cls.to_date = staticmethod(lambda x: datetime.datetime.fromisoformat(x))

    def setup_qcall(cls):
        # TODO(robnagler) change quest to support non contextlib
        # result so can bracket without with
        return cls.quest.import_and_start()

    def test_run_kinds(self):
        with self.setup_qcall() as qcall:
            a = qcall.db.query("run_kinds_and_values")
            self.pkeq(["sc_inj"], list(a.machines.keys()))
            self.pkeq(["impact"], list(a.machines.sc_inj.twins.keys()))
            self.pkeq(
                "impact^end_cov_x__px",
                a.machines.sc_inj.twins.impact.run_values[0],
            )

    def test_run_summary_by_id(self):
        with self.setup_qcall() as qcall:
            a = qcall.db.query("run_summary_by_id", run_summary_id=35002)
            self.pkre(".+/345ce931574f306208e8c8180e775be8.h5$", a.archive_path)

    def test_runs_by_date_and_values(self):
        with self.setup_qcall() as qcall:
            a = qcall.db.query(
                "runs_by_date_and_values",
                machine_name="sc_inj",
                twin_name="impact",
                min_max_values=self.PKDict(
                    {
                        "snapshot_end": self.PKDict(
                            # misses 2024-06-19 14:03:29.000000
                            max=self.to_date("2024-06-19T14:03:28"),
                            # gets 2024-06-19 13:42:21.000000
                            min=self.to_date("2024-06-19T13:42:21"),
                        ),
                        # excludes 2024-06-19 13:47:38.000000|63.119275042593
                        "impact^end_cov_x__px": self.PKDict(min=65),
                    }
                ),
                additional_run_values=["pv^SOLN:GUNB:212:BACT"],
            )
            self.pkeq(3, len(a.rows))
            self.pkeq("2024-06-19T13:42:21", a.rows[-1].snapshot_end.isoformat())
            self.pkeq("2024-06-19T13:58:07", a.rows[0].snapshot_end.isoformat())
            for r in a.rows:
                self.pkok(
                    r.run_values["impact^end_cov_x__px"] >= 65, "value < 65 row={}", r
                )
            self.pkeq(
                0.044200997724189985, a.rows[-1].run_values["pv^SOLN:GUNB:212:BACT"]
            )
