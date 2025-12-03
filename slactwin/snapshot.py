"""Snapshot server implementation

:copyright: Copyright (c) 2025 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp

import contextlib
import datetime
import pykern.sql_db
import slactwin.db
import slactwin.quest
import slactwin.run_importer


from pykern.pkasyncio import ActionLoop


class SnapshotAPI(slactwin.quest.API):
    """API entry points to be dispatched

    All entry points take ``api_args``, which is a dictionary of arguments.

    DateTimes should be passed in api_args as an int of seconds from the Unix epoch.

    Entry points return:

    api_result
        typically a dictionary, but could be an any Python data structure
    api_error
        is None on success. Otherwise, contains an string describing the error.
    """

    @pykern.api.util.subscription
    async def api_next_snapshot(self, api_args):
        try:
            q = asyncio.Queue()
            while not self.is_quest_end():
                r = await q.get()
                q.task_done()
                if r is None:
                    return None
                if isinstance(r, Exception):
                    raise r
                self.subscription.result_put(r)
        finally:
            if "session" in self:
                self.session.pkdel(_UPDATE_Q_KEY)
                self.session.pkdel(_SLICLET_KEY)


class DeviceLoop(pykern.pkasyncio.ActionLoop):
    pass


# DeviceLoop gathers PVs.
# another loop handles snapshots bound to the session
# like a sliclet
# deviceloop sends events for snapshots which get replied to
# maybe don't need the handler because is just marshalling the same datastructure
