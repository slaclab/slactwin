"""Import PV snapshots & Impact-T runs

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: See LICENSE file for details.
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import asyncio
import pykern.pkconfig
import pykern.pkjson
import pykern.util
import watchdog.events
import watchdog.observers


def init_tasks(loop):
    global _cfg

    _cfg = pykern.pkconfig.init(
        summary_dir=pykern.pkconfig.RequiredUnlessDev(
            None,
            pykern.util.cfg_absolute_dir,
            "where the summary files can be found",
        ),
    )
    if not (d := _cfg.summary_dir):
        d = pykern.util.dev_run_dir(init_tasks).join("summary").ensure(dir=True)
    _DbImporter(loop, summary_dir=d)


class _DbImporter(watchdog.events.FileSystemEventHandler):
    def __init__(self, loop, summary_dir):
        super()
        self.__loop = loop
        self.__queue = asyncio.Queue()
        self.__loop.call_soon_threadsafe(self.__parser)
        o = watchdog.observers.Observer()
        o.schedule(self, summary_dir, recursive=True)
        o.start()

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".json"):
            self.__loop.call_soon_threadsafe(self.__queue.put_nowait, event)

    async def __parser(self):
        def _import(path, summary):
            # "isotime": "2024-06-19T00:01:29-07:00",
            # summary.inputs["distgen:xy_dist:file"] #: "/sdf/group/ad/beamphysics/jytang/lume-impact-live-demo/configs/vcc_image/laser_06032024.txt"
            # summary.config.workdir #": "/sdf/scratch/users/j/jytang",
            # summary.config.impact_config # ": "//sdf/group/ad/beamphysics/lcls-lattice/impact/models/sc_inj/v1/ImpactT.yaml",
            # summary.config.distgen_input_file# ": "//sdf/group/ad/beamphysics/lcls-lattice/distgen/models/sc_inj/vcc_image/distgen.yaml"
            # summary.outputs.error # bool
            # summary.outputs.plot_file#": "//sdf/data/ad/ard/u/jytang/lume-impact-live/plot/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T00:01:29-07:00-dashboard.png",
            summary.outputs.archive  # ": "//sdf/data/ad/ard/u/jytang/lume-impact-live/archive/2024/06/19/2cfd76057f3f9f557df6e738d7dd08e9.h5"
            pass

        async for e in self.__queue:
            try:
                _import(e.src_path, pykern.pkjson.load_any(e.src_path))
            finally:
                self.__queue.task_done()
