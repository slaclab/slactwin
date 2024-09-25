"""Initialize modules once, in prescribed order

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import importlib

_done = False

_ORDER = "slactwin.db"


def import_and_init():
    """Import modules and call their ``init_module`` functions"""

    global _done

    if _done:
        return
    _done = True
    for m in (importlib.import_module(n) for n in _ORDER):
        m.init_module()
