"""Base class and common routines for other pkcli's to inherit/use.

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp


class CommandsBase:
    """Common functionality between all pkclis"""

    def __init__(self, *args, **kwargs):
        """Import and initialize slactwin app.

        Modules need to be imported/initialized in a specific order so
        configuration of one module can be used by another.
        """
        super().__init__(*args, **kwargs)
        from slactwin import modules

        modules.import_and_init()

    def quest_start(self):
        """Begin a request which wraps all APIs."""
        from slactwin import quest

        return quest.start()
