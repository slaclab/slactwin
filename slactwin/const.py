"""Constants

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp

RUN_VALUE_TAGS = frozenset(("impact", "pv"))
RUN_VALUE_SEP = "^"

DB_API_URI = "/slactwin-db"

DEV_DB_BASENAME = "slactwin.sqlite"
