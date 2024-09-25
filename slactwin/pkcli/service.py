"""Start slactwin services.

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import slactwin.pkcli


class Commands(slactwin.pkcli.CommandsBase):
    def db(self):
        """Start db api web server.

        This web server provides a friendly and secure API on top of
        the database of lume live runs. All reuqests for data from the
        databse should be routed through this service.
        """
        from pykern import http
        from slactwin import config, modules, db_api, quest

        http.server_start(
            attr_classes=quest.attr_classes(),
            api_classes=(db_api.DbAPI,),
            http_config=config.cfg().db_api,
            coros=(run_importer.start_notifier),
        )
