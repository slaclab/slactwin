"""Execution template.

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo.template.impactt_parser import ImpactTParser
import asyncio
import h5py
import impact
import pykern.pkio
import pykern.pkjson
import re
import sirepo.sim_data
import sirepo.template.impactt
import sirepo.template.lattice
import sirepo.util
import slactwin.db_api_client


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            frameCount=0,
            percentComplete=0,
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
    )


def sim_frame(frame_args):
    return sirepo.template.impactt.bunch_plot(
        frame_args,
        frame_args.frameIndex,
        _load_archive(frame_args).output["particles"][frame_args.plotName],
    )


def sim_frame_statAnimation(frame_args):
    return sirepo.template.impactt.stat_animation(_load_archive(frame_args), frame_args)


def sim_frame_summaryAnimation(frame_args):
    s = _summary_file(frame_args.runSummaryId)
    I = _load_archive(frame_args)
    with h5py.File(s.outputs.archive) as f:
        l = ImpactTParser().parse_file(f["/impact/input"].attrs["ImpactT.in"])
        l.models.simulation.visualizationBeamlineId = l.models.beamlines[0].id
    return PKDict(
        summary=PKDict(
            pv_mapping_dataframe=s.pv_mapping_dataframe,
            inputs=s.inputs,
            outputs=s.outputs,
            run_time=I.output["run_info"]["run_time"],
            Nbunch=I.header["Nbunch"],
            Nprow=I.header["Nprow"],
            Npcol=I.header["Npcol"],
        ).pkupdate(_summary_info(frame_args.runSummaryId)),
        lattice=_trim_beamline(l),
        particles=sirepo.template.impactt.output_info(l),
    )


def stateless_compute_db_api(data, **kwargs):
    try:
        return _db_api(**data.args)
    except ConnectionRefusedError:
        return PKDict(
            error="Could not connect to the database",
        )


def write_parameters(data, run_dir, is_parallel):
    pass


def _db_api(api_name, **kwargs):
    return asyncio.run(
        slactwin.db_api_client.DbAPIClient().post(
            api_name,
            kwargs["api_args"] if "api_args" in kwargs else PKDict(kwargs),
        ),
    )


def _load_archive(frame_args):
    return impact.Impact.from_archive(
        _summary_file(frame_args.runSummaryId).outputs.archive
    )


def _summary_file(run_summary_id):
    return pykern.pkjson.load_any(
        pykern.pkio.py_path(
            _db_api("run_summary_by_id", run_summary_id=run_summary_id).summary_path,
        ),
    )


def _summary_info(run_summary_id):
    s = _db_api("run_summary_by_id", run_summary_id=run_summary_id)
    m = re.search(r".*?/\d{4}/\d\d/\d\d/(.*?)-\d{4}", s.summary_path)
    return PKDict(
        description=m.group(1) if m else "",
        snapshot_end=s.snapshot_end,
    )


def _trim_beamline(data):
    # remove zero quads and trim beamline at STOP element
    util = sirepo.template.lattice.LatticeUtil(
        data, sirepo.sim_data.get_class("impactt").schema()
    )
    bl = []
    for i in data.models.beamlines[0]["items"]:
        el = util.id_map[i]
        if el.get("type") == "QUADRUPOLE":
            if el.rf_frequency == 0:
                continue
        bl.append(i)
        if el.get("type") == "STOP":
            break
    data.models.beamlines[0]["items"] = bl
    return data
