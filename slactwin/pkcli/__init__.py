"""Command wrapper

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp


class CommandsBase:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from slactwin import modules

        modules.import_and_init()

    def quest_start(self):
        from slactwin import quest

        return quest.start()
