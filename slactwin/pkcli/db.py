"""Database command-line utilities

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import slactwin.pkcli
import pykern.pkio


class Commands(slactwin.pkcli.CommandsBase):

    def insert_runs(self, archive_dir):
        """Load data from slactwin runs into db.

        Recursively searches `archive_dir` for any ``*.h5`` files,
        calling `slactwin.run_importer.insert_run_summary` for each
        file. Commits after each run summary import. Terminates on first
        run summary report in error or on successful completion.

        Typically, `archive_dir` points to the ``archive`` directory
        in the slactwin root which as subdirectories of the form
        YYYY/MM/DD, e.g. ``archive/2024/11/02/*.h5``.

        Args:
          archive_dir (str): directory containing archive ``.h5`` files
        """
        from slactwin import run_importer

        with self.quest_start() as qcall:
            for p in pykern.pkio.walk_tree(archive_dir, file_re=r"\.h5$"):
                c = False
                try:
                    run_importer.insert_run_summary(p, qcall)
                    c = True
                except Exception as e:
                    pkdlog("IGNORING exception={} path={} stack={}", e, p, pkdexc())
                finally:
                    qcall.db.commit_or_rollback(commit=c)
