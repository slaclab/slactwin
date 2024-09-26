"""Test run_importer notifier

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

import contextlib
import pytest

_NEW_SUMMARY_FILE = "lume-impact-live-demo-s3df-sc_inj-2024-06-19T07:03:29-07:00.json"


@pytest.mark.asyncio
async def test_notifier():
    import asyncio, shutil
    from slactwin import const, quest
    from pykern import pkunit, pkio, pkdebug
    from pykern.pkcollections import PKDict

    pkunit.data_dir().join(const.DEV_DB_BASENAME).copy(pkunit.work_dir())
    with quest.import_and_start() as qcall:
        from slactwin import run_importer

        asyncio.create_task(run_importer.start_notifier())
        await asyncio.sleep(0.1)
        with _timeout("first"):
            r = await run_importer.next_summary("sc_inj", "impact", None, qcall)
        pkunit.pkeq(1002, r.run_summary_id)
        # Wait for _process._init to complete. It has a sleep(1)
        await asyncio.sleep(1.5)
        # TODO(robnagler) works because summary_dir is last
        for s in pkio.sorted_glob(pkunit.data_dir().join("record1", "*")):
            pkdebug.pkdp(s)
            shutil.copytree(
                str(s),
                str(run_importer.cfg().summary_dir.new(basename=s.basename)),
                dirs_exist_ok=True,
            )
        pkdebug.pkdp("copy complete")
        with _timeout("second"):
            r = await run_importer.next_summary(
                "sc_inj", "impact", r.run_summary_id, qcall
            )
        pkunit.pkeq(2002, r.run_summary_id)


@contextlib.contextmanager
def _timeout(reason):
    import asyncio
    from pykern import pkunit, pkdebug

    async def _timer():
        k = False
        try:
            pkdebug.pkdp("start")
            await asyncio.sleep(2)
            pkdebug.pkdp("stop")
        except asyncio.CancelledError:
            pkdebug.pkdp("cancled")
            k = True
        finally:
            if not k:
                pkdebug.pkdlog("test step={} timed out", reason)
                asyncio.get_event_loop().stop()

    t = asyncio.create_task(_timer())
    yield
    t.cancel()
