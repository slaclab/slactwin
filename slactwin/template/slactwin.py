"""Execution template for SLAC TWIN. Responds to requests from the UI for database queries and plot data.

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
import sirepo.global_resources
import sirepo.sim_data
import sirepo.template.impactt
import sirepo.template.lattice
import sirepo.util
import slactwin.db_api_client


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def background_percent_complete(report, run_dir, is_running):
    """Called by the UI to get the status on a background job (report)

    Args:
        report (str): analysis model
        run_dir (py.path.Local): job run directory
        is_running (bool): True if the job is currently running
    Returns:
        PKDict: percentage complete summary info
    """
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
    """Plot request, provides bunch plot report data

    Args:
        frame_args (PKDict): contains elementAnimation field values as well as the full simulation instance and job run_dir
    Returns:
        PKDict: heatmap plot data and report labels
    """
    return sirepo.template.impactt.bunch_plot(
        frame_args,
        frame_args.frameIndex,
        _load_archive(frame_args).output["particles"][frame_args.plotName],
    )


def sim_frame_statAnimation(frame_args):
    """Specific plot request for the statAnimation plot

    Args:
        frame_args (PKDict): contains statAnimation field values as well as the full simulation instance and job run_dir
    Returns:
        PKDict: parameter plot data and report labels
    """
    return sirepo.template.impactt.stat_animation(_load_archive(frame_args), frame_args)


def sim_frame_summaryAnimation(frame_args):
    """Specific data request for the summaryAnimation model. Queries the database and loads the lume-impact archive for a specific runSummaryId.

    Args:
        frame_args (PKDict): contains a runSummaryId field value
    Returns:
        PKDict: PV values, simulation input values and simulation output values extracted from the summary file and Impact-T archive
    """
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
    """Request from the UI for database queries, ex. run_kinds_and_values or runs_by_date_and_values

    Args:
        data (PKDict): Contains api_name and api_args values for specific database queries.
    """
    try:
        return _db_api(**data.args)
    except ConnectionRefusedError:
        return PKDict(
            error="Could not connect to the database",
        )


def write_parameters(data, run_dir, is_parallel):
    """There is no code generation for this application

    Args:
        data (PKDict): simulation instance
        run_dir (py.path.Local): job run directory
        is_parallel (bool): is this for a background job?
    """
    pass


def _db_api(api_name, **kwargs):
    return asyncio.run(
        _db_api_client().post(
            api_name,
            kwargs["api_args"] if "api_args" in kwargs else PKDict(kwargs),
        ),
    )


def _db_api_client():
    return slactwin.db_api_client.DbAPIClient(
        # TODO(e-carlin): sid is not used but is required arg. Make optional.
        # TODO(e-carlin): nested resources in global_resources should be converted to PKDict
        # by the api infrastructure.
        http_config=PKDict(
            sirepo.global_resources.for_simulation(SIM_TYPE, "notused").db_api
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
    """Returns a descriptive name and date for the runSummaryId
    Constructs the description from the summary filename, ex. lume-impact-live-demo-s3df-sc_inj
    """
    s = _db_api("run_summary_by_id", run_summary_id=run_summary_id)
    m = re.search(r".*?/\d{4}/\d\d/\d\d/(.*?)-\d{4}", s.summary_path)
    return PKDict(
        description=m.group(1) if m else "",
        snapshot_end=s.snapshot_end,
    )


def _trim_beamline(data):
    """Updates the lume-impact lattice displayed from the UI.
    Remove zero quads and trim beamline at STOP element
    """
    util = sirepo.template.lattice.LatticeUtil(
        data, sirepo.sim_data.get_class("impactt").schema()
    )
    bl = []
    for i in data.models.beamlines[0]["items"]:
        el = util.id_map[i]
        if el.get("type") == "QUADRUPOLE":
            if el.rf_frequency == 0:
                # TODO(pjm): should insert a drift for the same length
                continue
        bl.append(i)
        if el.get("type") == "STOP":
            break
    data.models.beamlines[0]["items"] = bl
    return data
