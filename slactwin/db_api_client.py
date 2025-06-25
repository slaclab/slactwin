"""Client to access database over pykern.api


:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.api.client
import sirepo.global_resources
import slactwin.config


def for_job_cmd():
    c = sirepo.global_resources.for_simulation("slactwin", "notused")
    return DbAPIClient(
        # TODO(e-carlin): sid is not used but is required arg. Make optional.
        # TODO(e-carlin): nested resources in global_resources should be converted to PKDict
        # by the api infrastructure.
        http_config=PKDict(c.db_api).pkupdate(
            request_config=PKDict(c.db_api_request_config)
        ),
    )


class DbAPIClient(pykern.api.client.Client):
    """See `pykern.api.client.Client` for how to make API calls."""

    def __init__(self, http_config=None):
        # TODO(e-carlin): In job_agent it is too late to properly setup env
        # for pkconfig.init to work. pkconfig.init has already been called (_raw_values is set)
        # so we can't set env and then get it here.
        super().__init__(http_config or slactwin.config.cfg().db_api)
