"""common config utilities

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkasyncio
import pykern.pkconfig
import pykern.pkunit
import pykern.util
import slactwin.const

_cfg = None


def init_module():
    if pykern.pkconfig.channel_in("dev"):
        global _dev_root_d

        _dev_root_d = pykern.util.dev_run_dir(dev_path)

    global _cfg

    _cfg = pykern.pkconfig.init(
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
    )


def cfg():
    return _cfg


def dev_path(path, **ensure_kwargs):
    return _dev_root_d.join(path)
