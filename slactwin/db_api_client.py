"""Client to access database over HTTP


:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.http
import slactwin.config


class DbAPIClient(pykern.http.HTTPClient):
    """See `pykern.http.HTTPClient` for how to make API calls."""

    def __init__(self, http_config=None):
        # TODO(e-carlin): In job_agent it is too late to properly setup env
        # for pkconfig.init to work. pkconfig.init has already been called (_raw_values is set)
        # so we can't set env and then get it here.
        super().__init__(http_config or slactwin.config.cfg().db_api)
