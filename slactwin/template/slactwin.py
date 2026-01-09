"""Execution template for SLAC TWIN. Responds to requests from the UI for database queries and plot data.

:copyright: Copyright (c) 2024-2025 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pmd_beamphysics import ParticleGroup
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo.template import template_common
from sirepo.template.impactt_parser import ImpactTParser
import asyncio
import datetime
import h5py
import impact
import pykern.pkio
import pykern.pkjson
import pytz
import re
import sirepo.global_resources
import sirepo.sim_data
import sirepo.sim_run
import sirepo.simulation_db
import sirepo.template.impactt
import sirepo.template.lattice
import sirepo.util
import slactwin.db_api_client
import slactwin.util


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_NONE = "None"
LIVE_OUT = "live.json"


def background_percent_complete(report, run_dir, is_running):
    """Called by the UI to get the status on a background job (report)

    Args:
        report (str): analysis model
        run_dir (py.path.Local): job run directory
        is_running (bool): True if the job is currently running
    Returns:
        PKDict: percentage complete summary info and outputInfo
    """

    rv = PKDict(
        percentComplete=100,
        frameCount=1,
    )
    is_live = (
        sirepo.simulation_db.read_json(
            run_dir.join(template_common.INPUT_BASE_NAME)
        ).models.searchSettings.isLive
        == "1"
    )
    if is_live:
        f = run_dir.join(LIVE_OUT)
        if f.exists():
            rv.outputInfo = pykern.pkjson.load_any(f)
    return rv


def sim_frame(frame_args):
    """Plot request, provides bunch plot report data

    Args:
        frame_args (PKDict): contains elementAnimation field values as well as the full simulation instance and job run_dir
    Returns:
        PKDict: heatmap plot data and report labels
    """
    # this is a generic openPMD plotter, so usable by impact and rslume-elegant
    return sirepo.template.impactt.bunch_plot(
        frame_args,
        frame_args.frameIndex,
        _twin_implementation(frame_args.runSummaryId)
        .load_archive()
        .output["particles"][frame_args.plotName],
    )


def sim_frame_statAnimation(frame_args):
    """Specific plot request for the statAnimation plot

    Args:
        frame_args (PKDict): contains statAnimation field values as well as the full simulation instance and job run_dir
    Returns:
        PKDict: parameter plot data and report labels
    """

    return _twin_implementation(frame_args.runSummaryId).stat_animation(frame_args)


def sim_frame_summaryAnimation(frame_args):
    """Specific data request for the summaryAnimation model. Queries the database and loads the lume-impact archive for a specific runSummaryId.

    Args:
        frame_args (PKDict): contains a runSummaryId field value
    Returns:
        PKDict: PV values, simulation input values and simulation output values extracted from the summary file and Impact-T archive
    """

    return _twin_implementation(frame_args.runSummaryId).summary_animation(frame_args)


def stateful_compute_create_sim_for_run_summary(data, **kwargs):
    c = _SIM_DATA.sim_db_client()

    def _put_lib_file(tmp_dir, model_name, model, file_name):
        n = f"{tmp_dir.join(file_name).computehash()}.txt"
        c.put(
            c.LIB_DIR,
            _SIM_DATA.lib_file_name_with_model_field(
                model_name,
                "filename",
                n,
            ),
            tmp_dir.join(file_name),
            sim_type="impactt",
        )
        return n

    def _sim_name(machine_name, timestamp):
        # TODO(pjm): how should the time be encoded in the simulation name?
        # SLAC local time (Pacific) or GMT?
        # (The UI would be showing SLACTwin times in localtime for comparison)
        t = (
            timestamp.astimezone(pytz.timezone("US/Pacific"))
            .isoformat()
            .replace("T", " ")
        )
        return f"{machine_name}-{t}"

    def _update_sim(run_summary_id, run_summary_url):
        s = _db_api("run_summary_by_id", run_summary_id=run_summary_id)
        k = _db_api("run_kind_by_id", run_kind_id=s.run_kind_id)
        t = datetime.datetime.fromtimestamp(s.snapshot_end)
        return PKDict(
            name=_sim_name(k.machine_name, t),
            folder=f"/SLACTwin/{k.machine_name}/{t.strftime('%Y-%m')}",
            notes=f"Imported from $\\href{{ {run_summary_url} }}{{ \\text{{SLACTwin}} }}$",
        )

    with sirepo.sim_run.tmp_dir() as t:
        # TODO(pjm): handle by twin_name
        I = impact.Impact(
            workdir=str(t),
            use_temp_dir=False,
        )
        I.load_archive(_archive_path(data.args.runSummaryId))
        I.numprocs = 1
        I.configure()
        I.write_input()
        d = ImpactTParser().parse_file(pykern.pkio.read_text(t.join("ImpactT.in")))
        for m in d.models.elements:
            if m.type != "WRITE_BEAM" and m.get("filename"):
                m.filename = _put_lib_file(t, m.type, m, m.filename)
        d.models.distribution.filename = _put_lib_file(
            t, "distribution", d.models.distribution, "partcl.data"
        )
        d.models.simulation.pkupdate(
            _update_sim(data.args.runSummaryId, data.args.runSummaryUrl)
        )
        return PKDict(
            sim_data=d,
        )


def stateless_compute_db_api(data, **kwargs):
    """Request from the UI for database queries, ex. run_values or runs_by_date_and_values

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

    if data.report == "animation" and data.models.searchSettings.isLive == "1":
        pykern.pkio.write_text(
            run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
            template_common.render_jinja(SIM_TYPE, data.models),
        )
    return None


def _db_api(api_name, **kwargs):
    async def _target():
        c = await slactwin.db_api_client.for_job_cmd().connect()
        return await c.call_api(
            api_name,
            kwargs["api_args"] if "api_args" in kwargs else PKDict(kwargs),
        )

    return asyncio.run(_target())


def _archive_path(run_summary_id):
    return _db_api("run_summary_by_id", run_summary_id=run_summary_id).archive_path


def _openpmd_particles(archive):
    def _default_columns(info):
        if info.name == "final_particles":
            info.x = "delta_z"
            info.y = "delta_energy"
        else:
            info.x = "x"
            info.y = "y"
        return info

    res = []
    visited = set()
    for idx, n in enumerate(
        ["initial_particles", "final_particles"] + list(archive.output.particles.keys())
    ):
        if n in visited:
            continue
        visited.add(n)
        res.append(
            _default_columns(
                PKDict(
                    modelKey=f"elementAnimation{idx}",
                    reportIndex=idx,
                    report="elementAnimation",
                    name=n,
                    frameCount=1,
                    isHistogram=True,
                    # TODO(pjm): move to more general (openpmd_util)
                    columns=sirepo.template.impactt._BUNCH_COLUMNS,
                )
            )
        )
    return res


def _summary_data(run_summary_id):
    res = slactwin.util.summary_from_archive(_archive_path(run_summary_id))
    res.pv_mapping_dataframe = PKDict(res.pv_mapping_dataframe.to_dict())
    return res


def _summary_info(run_summary_id):
    s = _db_api("run_summary_by_id", run_summary_id=run_summary_id)
    k = _db_api("run_kind_by_id", run_kind_id=s.run_kind_id)
    return PKDict(
        description=f"{k.machine_name} {k.twin_name}",
        snapshot_end=s.snapshot_end,
    )


def _twin_implementation(run_summary_id):
    s = _db_api("run_summary_by_id", run_summary_id=run_summary_id)
    k = _db_api("run_kind_by_id", run_kind_id=s.run_kind_id)
    if k.twin_name == "impact":
        return _ImpactT(run_summary_id)
    if k.twin_name == "elegant":
        return _Elegant(run_summary_id)
    if k.twin_name == "pytao":
        return _PyTao(run_summary_id)
    assert False, f"unhandled twin_name: {k.twin_name}"


def _update_dataframe(data, dataframe):
    util = sirepo.template.lattice.LatticeUtil(
        data, sirepo.sim_data.get_class("elegant").schema()
    )
    el_by_name = PKDict()
    for i in data.models.beamlines[0]["items"]:
        el = util.id_map[i]
        el_by_name[el.name] = el._id
    dataframe.el_id = PKDict()
    for idx, n in dataframe.element.items():
        dataframe.el_id[str(idx)] = el_by_name.get(n)
    return dataframe


class _Elegant:

    def __init__(self, run_summary_id):
        self.run_summary_id = run_summary_id

    def load_archive(self):
        from rslume import elegant

        return elegant.Elegant.from_archive(_archive_path(self.run_summary_id))

    def stat_animation(self, frame_args):
        E = self.load_archive()
        stats = E.output["stats"]
        plots = PKDict()
        if frame_args.x == _NONE:
            frame_args.x = "s"
        for f in ("x", "y1", "y2", "y3", "y4", "y5"):
            if frame_args[f] == _NONE:
                continue
            units = E.output.stats_unit[frame_args[f]]
            if units and str(units) and str(units) != "1":
                if re.search(r"[_{}\\]", units):
                    units = f" [$\\mathsf{{{units}}}$]"
                else:
                    units = f" [{units}]"
            else:
                units = ""
            p = stats[frame_args[f]]
            plots[f] = PKDict(
                label=f"${E.output.stats_label[frame_args[f]]}${units}",
                dim=f,
                points=p.tolist(),
            )
        return template_common.parameter_plot(
            x=plots.x.points,
            plots=[p for p in plots.values() if p.dim != "x"],
            model=frame_args,
            plot_fields=PKDict(
                dynamicYLabel=True,
                title="",
                y_label="",
                x_label=plots.x.label,
            ),
        )

    def summary_animation(self, frame_args):
        s = _summary_data(self.run_summary_id)
        E = self.load_archive()
        return PKDict(
            summary=PKDict(
                pv_mapping_dataframe=_update_dataframe(
                    E._input, s.pv_mapping_dataframe
                ),
                summary_columns=self._summary_columns(),
                summary_text=self._summary_text(s, E, E._input.models),
                # TODO(pjm): save run_time
                # run_time_minutes=I.output["run_info"]["run_time"] / 60,
                run_time_minutes=4.1,
            ).pkupdate(_summary_info(self.run_summary_id)),
            lattice=PKDict(
                models=E._input.models,
            ),
            particles=_openpmd_particles(E),
            stat_columns=[_NONE] + list(E.output["stats"].keys()),
        )

    def _summary_text(self, summary, E, models):
        return [
            f"{summary.outputs.end_Particles:,} macroparticles",
            # TODO(pjm): species info
            f"Total charge: {summary.outputs.end_Charge * 1e12:.1f} pC",
            # TODO(pjm): processors used
            f"Final emittance(x, y): {summary.outputs.end_enx * 1e6:.3f}, {summary.outputs.end_eny * 1e6:.3f} µm",
            f"Final bunch length: {summary.outputs.end_Ss * 1e3:.3f} mm",
        ]

    def _summary_columns(self):
        return [
            ["Variable", "name"],
            ["PV Name", "device_pv_name"],
            ["PV Value", "pv_value"],
            ["Field", "attribute"],
            ["elegant Value", "value"],  # TODO(pjm): units
            ["elegant Factor", "factor"],
        ]


class _PyTao:

    def __init__(self, run_summary_id):
        self.run_summary_id = run_summary_id

    def load_archive(self):
        res = PKDict()
        with h5py.File(_archive_path(self.run_summary_id), "r") as f:
            res.output = PKDict(stats=PKDict(), particles=PKDict())
            for c in f["/pytao/stats"]:
                res.output.stats[c] = f[f"/pytao/stats/{c}"][:]
            res.lattice = pykern.pkjson.load_any(f["/pytao"].attrs["lattice"])
            for p in f["/pytao/particles"]:
                res.output.particles[p] = ParticleGroup(h5=f[f"/pytao/particles/{p}"])
        return res

    def stat_animation(self, frame_args):
        # TODO(pjm): consolidate w/_Elegant
        a = self.load_archive()
        stats = a.output["stats"]
        plots = PKDict()
        if frame_args.x == _NONE:
            frame_args.x = "s"
        for f in ("x", "y1", "y2", "y3", "y4", "y5"):
            if frame_args[f] == _NONE:
                continue
            # units = E.output.stats_unit[frame_args[f]]
            units = ""
            if units and str(units) and str(units) != "1":
                if re.search(r"[_{}\\]", units):
                    units = f" [$\\mathsf{{{units}}}$]"
                else:
                    units = f" [{units}]"
            else:
                units = ""
            p = stats[frame_args[f]]
            plots[f] = PKDict(
                # label=f"${a.output.stats_label[frame_args[f]]}${units}",
                label=frame_args[f],
                dim=f,
                points=p.tolist(),
            )
        return template_common.parameter_plot(
            x=plots.x.points,
            plots=[p for p in plots.values() if p.dim != "x"],
            model=frame_args,
            plot_fields=PKDict(
                dynamicYLabel=True,
                title="",
                y_label="",
                x_label=plots.x.label,
            ),
        )

    def summary_animation(self, frame_args):
        s = _summary_data(self.run_summary_id)
        a = self.load_archive()
        return PKDict(
            summary=PKDict(
                pv_mapping_dataframe=_update_dataframe(
                    PKDict(
                        models=a.lattice,
                    ),
                    s.pv_mapping_dataframe,
                ),
                summary_columns=self._summary_columns(),
                summary_text=[
                    "summary text goes here",
                ],
                # TODO(pjm): save run_time
                # run_time_minutes=I.output["run_info"]["run_time"] / 60,
                run_time_minutes=3.1,
            ).pkupdate(_summary_info(self.run_summary_id)),
            lattice=PKDict(
                models=a.lattice,
            ),
            particles=_openpmd_particles(a),
            stat_columns=[_NONE] + list(a.output.stats.keys()),
        )

    def _summary_columns(self):
        return [
            ["Variable", "name"],
            ["PV Name", "device_pv_name"],
            ["PV Value", "pv_value"],
            ["Field", "attribute"],
            ["PyTao Value", "value"],  # TODO(pjm): units
            ["PyTao Factor", "factor"],
        ]


class _ImpactT:

    def __init__(self, run_summary_id):
        self.run_summary_id = run_summary_id

    def load_archive(self):
        return impact.Impact.from_archive(_archive_path(self.run_summary_id))

    def stat_animation(self, frame_args):
        return sirepo.template.impactt.stat_animation(self.load_archive(), frame_args)

    def summary_animation(self, frame_args):
        s = _summary_data(self.run_summary_id)
        I = self.load_archive()
        with h5py.File(_archive_path(self.run_summary_id)) as f:
            l = ImpactTParser().parse_file(f["/impact/input"].attrs["ImpactT.in"])
            l.models.simulation.visualizationBeamlineId = l.models.beamlines[0].id
        return PKDict(
            summary=PKDict(
                pv_mapping_dataframe=s.pv_mapping_dataframe,
                summary_columns=self._summary_columns(),
                summary_text=self._summary_text(s, I, l.models),
                run_time_minutes=I.output["run_info"]["run_time"] / 60,
            ).pkupdate(_summary_info(self.run_summary_id)),
            lattice=self._trim_beamline(l, s.pv_mapping_dataframe),
            particles=sirepo.template.impactt.output_info(l),
            stat_columns=sirepo.template.impactt.stat_columns(I),
        )

    def _summary_columns(self):
        return [
            ["Variable", "Variable"],
            ["PV Name", "device_pv_name"],
            ["PV Value", "pv_value", "pv_unit"],
            ["IMPACT-T Name", "impact_name"],
            ["IMPACT-T Value", "impact_value", "impact_unit"],
            ["IMPACT-T Offset", "impact_offset"],
            ["IMPACT-T Factor", "impact_factor"],
        ]

    def _summary_text(self, summary, I, models):
        """Returns a descriptive name and date for the runSummaryId
        Constructs the description from the summary filename, ex. lume-impact-live-demo-s3df-sc_inj
        """
        change_timesteps = PKDict()
        timestep_pos = None
        timestep_dt = None
        for el in models.elements:
            if el.type == "CHANGE_TIMESTEP":
                change_timesteps[el._id] = el
        for idx, el_id in enumerate(models.beamlines[0]["items"]):
            if el_id in change_timesteps:
                timestep_pos = models.beamlines[0].positions[idx].elemedge
                timestep_dt = change_timesteps[el_id].dt
        return [
            f"{I.header['Np']:,} macroparticles",
            # TODO(pjm): actually electrons, not "other"
            f"{I.header['Nbunch']} bunch{'es' if I.header['Nbunch'] > 1 else ''} of {models.beam.particle}",
            f"Total charge: {I.total_charge * 1e12:.1f} pC",
            f"Processor domain: {I.header['Nprow']} x {I.header['Npcol']} = {I.header['Nprow'] * I.header['Npcol']} CPUs",
            f"Space charge grid: {models.simulationSettings.Nx} x {models.simulationSettings.Ny} x {models.simulationSettings.Nz}",
            (
                f"Timestep: {models.simulationSettings.Dt * 1e12:.1f} ps to {timestep_pos} m, then {timestep_dt * 1e12:.1f} ps until the end"
                if timestep_pos
                else ""
            ),
            f"Final emittance(x, y): {summary.outputs.end_norm_emit_x * 1e6:.3f}, {summary.outputs.end_norm_emit_y * 1e6:.3f} µm",
            f"Final bunch length: {summary.outputs.end_sigma_z * 1e3:.2f} mm",
        ]

    def _trim_beamline(self, data, dataframe):
        """Updates the lume-impact lattice displayed from the UI.
        Trims beamline at STOP element. Removes dataframes for elements after the STOP element.
        """

        util = sirepo.template.lattice.LatticeUtil(
            data, sirepo.sim_data.get_class("impactt").schema()
        )
        bl = []
        found_stop = False
        el_by_name = PKDict()
        # TODO(pjm): assumes sim has single beamline
        for i in data.models.beamlines[0]["items"]:
            el = util.id_map[i]
            el_by_name[el.name] = el._id
            if not found_stop:
                bl.append(i)
            if el.get("type") == "STOP":
                found_stop = True

        # remove dataframe rows for elements after the STOP element
        remove_frames = set()
        dataframe.el_id = PKDict()
        for k in dataframe.impact_name:
            n = dataframe.impact_name[k].split(":")[0]
            el_id = el_by_name.get(n)
            if el_id and el_id not in bl:
                remove_frames.add(k)
            dataframe.el_id[k] = el_id
        for k in remove_frames:
            for f in dataframe.values():
                del f[k]
        data.models.beamlines[0]["items"] = bl
        return data
