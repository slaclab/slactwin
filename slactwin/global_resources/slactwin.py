"""Job command resources

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import pykern.pkasyncio
import pykern.pkconfig
import sirepo.global_resources

_cfg = None


class Allocator(sirepo.global_resources.AllocatorBase):
    def _get(self):
        return PKDict(
            db_api=PKDict(
                api_uri=_cfg.db_api.api_uri,
                auth_secret=_cfg.db_api.auth_secret,
                tcp_ip=_cfg.db_api.tcp_ip,
                tcp_port=_cfg.db_api.tcp_port,
            ),
        )

    def _redact_for_gui(self, resources):
        return PKDict()


def _init():
    global _cfg
    _cfg = pykern.pkconfig.init(
        # TODO(e-carlin): This is copied from slactwin.config. Share.
        db_api=PKDict(
            api_uri=("/slactwin-api-v1", str, "URI for API requests"),
            auth_secret=pykern.pkconfig.RequiredUnlessDev(
                "development_secret",
                str,
                "secret required to access db_api",
            ),
            tcp_ip=(None, pykern.pkasyncio.cfg_ip, "IP address for server"),
            tcp_port=(9020, pykern.pkasyncio.cfg_ip, "port of server"),
        )
    )


_init()
