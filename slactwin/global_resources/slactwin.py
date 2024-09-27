"""Resources for the slactwin simulation type.

Configuration for slactwin job_cmds to communicate with the slactwin
db service.

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import copy
import pykern.pkasyncio
import pykern.pkconfig
import sirepo.global_resources

_cfg = None


class Allocator(sirepo.global_resources.AllocatorBase):
    """Manages access to resources."""

    def _get(self):
        """Resources for job_cmds and the gui.

        Returns:
          PKDict: The resources.
        """
        return copy.deepcopy(_cfg)

    def _redact_for_gui(self, resources):
        """Redact resources sent to the GUI.

        Resources sent to the GUI are easily read by the user so we
        redact any sensitive information. For example, the authentication
        secret used by job_cmds to communicate with the slactwin db
        service should not be exposed to the user through the GUI.

        Returns:
          PKDict: Resources that are safe to send to the GUI.
        """
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
        ),
        db_api_request_config=PKDict(
            request_timeout=(
                600,
                pykern.pkconfig.parse_seconds,
                "Long polling timeout for job_cmd",
            ),
        ),
    )


_init()
