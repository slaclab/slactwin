"""Import PV snapshots & Impact-T runs

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import slactwin.pkcli
import pykern.pkio


class Commands(slactwin.pkcli.CommandsBase):

    def insert_runs(self, summary_dir):
        from slactwin import run_importer

        with self.quest_start() as qcall:
            for p in pykern.pkio.walk_tree(summary_dir, file_re=r"\.json$"):
                c = False
                try:
                    run_importer.insert_run_summary(p, qcall)
                    c = True
                except Exception as e:
                    pkdlog("ERROR path={}", p)
                    raise
                finally:
                    qcall.db.commit_or_rollback(commit=c)
