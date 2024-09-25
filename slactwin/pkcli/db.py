"""Database command-line utilities

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import slactwin.pkcli
import pykern.pkio


class Commands(slactwin.pkcli.CommandsBase):

    def insert_runs(self, summary_dir):
        """Load data from lume-impact-live-demo runs into db.

        Recursively searches `summary_dir` for any ``*.json`` files,
        calling `slactwin.run_importer.insert_run_summary` for each
        file. Commits after each run summary import. Terminates on first
        run summary report in error or on successful completion.

        Typically, `summary_dir` points to the ``summary`` directory
        in the lume-impact-live-demo root which as subdirectories of the form
        YYYY/MM/DD, e.g. ``summary/2024/11/02/*.json``.

        Args:
          summary_dir (str): directory containing summary ``.json`` files
        """
        from slactwin import run_importer

        with self.quest_start() as qcall:
            for p in pykern.pkio.walk_tree(summary_dir, file_re=r"\.json$"):
                c = False
                try:
                    rv = run_importer.insert_run_summary(p, qcall)
                    c = True
                except Exception as e:
                    pkdlog("ERROR path={}", p)
                    raise
                finally:
                    qcall.db.commit_or_rollback(commit=c)
        return rv
