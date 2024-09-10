"""Db_API client

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.http
import slactwin.config


class DbAPIClient(pykern.http.HTTPClient):

    def __init__(self):
        super().__init__(slactwin.config.cfg().db_api)
