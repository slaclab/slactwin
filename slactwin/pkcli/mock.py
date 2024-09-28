"""Support for testing

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkio
import time
import slactwin.pkcli


# Needs a "." so purebasename works
_LIVE_QUEUED = ".queued"


class Commands(slactwin.pkcli.CommandsBase):

    def live(self, period=30):
        """Mock the lume-live directory

        Example:
            cd ~/src/slaclab/slactwin/run
            tar xzf ~/tmp/iana.tgz
            mv iana/{archive,plot,snapshot,summary} .
            rm -rf iana
            rm slactwin.sqlite
            slactwin mock live
        Args:
            period (float): how often to move summary files into position
        """

        from slactwin import run_importer

        def _queued(summary_dir):
            for i, p in enumerate(
                pykern.pkio.walk_tree(summary_dir, file_re=r"\.json$")
            ):
                if i == 0:
                    # first file needs to be there to populate the db
                    continue
                n = p.new(basename=p.basename + _LIVE_QUEUED)
                p.rename(n)
            for p in pykern.pkio.walk_tree(summary_dir, file_re=f"{_LIVE_QUEUED}$"):
                yield p

        for p in _queued(run_importer.cfg().summary_dir):
            time.sleep(period)
            t = p.new(basename=p.purebasename)
            p.rename(p.new(basename=p.purebasename))
            pkdlog("{}", t)
