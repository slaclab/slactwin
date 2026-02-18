"""Simple Bmad runner

:copyright: Copyright (c) 2025 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pmd_beamphysics import ParticleGroup
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pytao import Tao
from slactwin.simrun_util import Archiver
import h5py
import numpy
import os
import pmd_beamphysics
import pykern.pkjson
import re
import slactwin.simrun_util

_STAT_FIELDS = [
    "a.beta",
    "a.alpha",
    "a.eta",
    "a.etap",
    "a.gamma",
    "a.phi",
    "b.beta",
    "b.alpha",
    "b.eta",
    "b.etap",
    "b.gamma",
    "b.phi",
    "x.eta",
    "x.etap",
    "y.eta",
    "y.etap",
    "s",
    "e_tot",
    "p0c",
]

_TWIN_NAME = "bmad"


def run(
    model_name,
    pv_filename,
    start_element_name,
    end_element_name,
    watches="",
    beam_in=None,
    out_dir=None,
):
    """
    Run a Bmad simulation between two lattice elements.

    This function executes a beam dynamics simulation for the specified
    model using process variable (PV) settings provided in a JSON file.

    Example:
        slactwin simrun-bmad run cu_hxr cu_hxr-2025-12-04T08:14:13-08:00.json \
            WS02 ENDBC1 --watches=BC1CBEG:BC1CEND

    Args:
        model_name (str):
            Name of the accelerator model to use (e.g., "cu_spec", "cu_hxr").

        pv_filename (str):
            Path to a JSON file containing process variable (PV) values
            used to configure the model before running the simulation.

        start_element_name (str):
            Name of the lattice element where beam tracking begins.

        end_element_name (str):
            Name of the lattice element where beam tracking stops.

        watches (str, optional):
            Optional colon-separated list specifying additional points along the
            lattice to save particle data.

        beam_in (object, optional):
            Optional input distribution file to use instead of
            the model’s default initial beam

        out_dir (str, optional):
            Directory where simulation output files will be written. Files are
            written to subdirectories based on the timestamp. (YYYY/MM/DD/)
    """

    def evaluate_tao(tao, cmds, pvinfo):
        res = []
        ele_names = tao.lat_list("*", "ele.name", flags="-no_slaves")
        run_cmds = []
        for cmd in cmds:
            n = slactwin.simrun_util.parse_element_name_from_cmd(cmd)
            if n and (n != "beginning" and n not in ele_names):
                pkdc("skip cmd: {}", cmd)
                continue
            run_cmds.append(cmd)
            p = slactwin.simrun_util.parse_cmd(cmd)
            if p and p[0] in pvinfo:
                for c in pvinfo[p[0]]:
                    if c.attribute == p[1]:
                        res.append(c)
                        c.value = p[2]
        if beam_in:
            run_cmds.append(f"set beam_init position_file = '{beam_in}'")
            # TODO(pjm): use tmp
            # fn = '/home/vagrant/tmp/bmad-beam-in.txt'
            # ParticleGroup(beam_in).write_bmad(fn)
            # run_cmds.append(f"set beam_init position_file = '{fn}'")
        run_cmds += [
            f"set beam_init track_start = {start_element_name}",
            f"set beam_init track_end = {end_element_name}",
            "set beam_init saved_at = MARKER::* MONITOR::*",
            # TODO(pjm): command line arg for particle count
            "set beam_init n_particle = 10000",
            "set global track_type = beam",
            "set global track_type = single",
        ]
        for cmd in run_cmds:
            pkdc("cmd: {}", cmd)
            tao.cmd(cmd)
        idx = {n: i for i, n in enumerate(ele_names)}
        return sorted(res, key=lambda x: idx.get(x.name, -1)), run_cmds

    # TODO(pjm): could pass in path to private repo
    assert "LCLS_LATTICE" in os.environ
    cmds, pvinfo, _ = slactwin.simrun_util.build_commands(model_name, pv_filename)
    taoinit = f"-init $LCLS_LATTICE/bmad/models/{model_name}/tao.init -slice {start_element_name}:{end_element_name} -noplot"
    tao = Tao(taoinit)
    pv_summary, run_cmds = evaluate_tao(tao, cmds, pvinfo)
    a = Archiver(
        pv_filename,
        _TWIN_NAME,
        model_name,
    )
    outputs = _archive(
        a.archive_path("."),
        tao,
        [start_element_name, end_element_name]
        + (watches.split(":") if watches else []),
        taoinit,
        run_cmds,
    )
    a.add_summary(pv_summary, outputs, out_dir)


def _archive(filename, tao, watches, taoinit, run_cmds):

    def _add_bunch_params(res, group):
        b = [tao.bunch_params(i) for i in _tao_lat_list(tao, "ele.ix_ele")]
        for idx in range(len(b)):
            if b[idx]["s"] == -1:
                b[idx] = b[idx + 1]
                assert b[idx]["s"] != -1
        for k in b[0]:
            if k in res:
                continue
            res[k] = [b[i][k] for i in range(len(b))]
            group.create_dataset(k, data=res[k])

    def _add_element_values(res, group):
        for c in _STAT_FIELDS:
            res[c] = tao.lat_list("*", f"ele.{c}")
            if c == "s":
                res[c] = res[c] - res[c][0]
            group.create_dataset(c, data=res[c])

    stats = PKDict()
    with h5py.File(filename, "w") as f:
        g = f.create_group(_TWIN_NAME)
        o = g.create_group("output")
        gs = o.create_group("stats")
        _add_element_values(stats, gs)
        _add_bunch_params(stats, gs)
        for idx, n in enumerate(watches):
            P = pmd_beamphysics.ParticleGroup(data=tao.bunch_data(n))
            name = (
                "initial_particles"
                if idx == 0
                else "final_particles" if idx == 1 else n
            )
            P.write(f, name=f"/{_TWIN_NAME}/output/particles/{name}")
        i = g.create_group("input")
        i.attrs["lattice"] = pykern.pkjson.dump_pretty(_tao_lattice(tao, watches))
        i.attrs["taoCommands"] = pykern.pkjson.dump_pretty(run_cmds)
        i.attrs["taoInit"] = taoinit
    return PKDict({f"end_{c}": stats[c][-1] for c in stats})


def _tao_lat_list(tao, field):
    return tao.lat_list("*", field)


def _tao_lattice(tao, watches):
    _FLAGS = "-array_out -track_only"
    _IGNORE_ELEMENTS = set(("BEGINNING_ELE", "MARKER", "MONITOR"))

    def _map_attrs():
        attrs = PKDict()
        for k in (
            ["sbend", "angle"],
            ["sbend", "e1"],
            ["sbend", "e2"],
            ["quadrupole", "k1"],
            ["*", "l"],
            ["lcavity", "voltage"],
        ):
            i = [
                int(v) for v in tao.lat_list(f"{k[0]}::*", f"ele.ix_ele", flags=_FLAGS)
            ]
            attrs[k[1]] = dict(
                zip(
                    i,
                    [
                        float(v)
                        for v in tao.lat_list(f"{k[0]}::*", f"ele.{k[1]}", flags=_FLAGS)
                    ],
                )
            )
        return attrs

    def _build_models():
        attrs = _map_attrs()
        ele_ids = tao.lat_list("*", "ele.ix_ele", flags=_FLAGS)

        next_id = 1
        models = PKDict(
            elements=[],
            beamlines=[
                PKDict(
                    id=next_id,
                    items=[],
                ),
            ],
            simulation=PKDict(
                visualizationBeamlineId=next_id,
            ),
        )
        next_id += 1
        visited = PKDict()

        for ele_id in ele_ids:
            head = tao.ele_head(ele_id)
            ix_ele = head["ix_ele"]
            if head["name"] in visited:
                el = visited[head["name"]]
                assert el.l == attrs.l[ix_ele]
                assert el.type == head["key"].upper()
            else:
                el = PKDict(
                    _id=next_id,
                    type=head["key"].upper(),
                    l=attrs.l[ix_ele],
                    # name=head["name"],
                    name=re.sub(r"#.*", "", head["name"]),
                )
                if el.type in _IGNORE_ELEMENTS and el.name not in watches:
                    continue
                for k in attrs:
                    if ix_ele in attrs[k]:
                        el[k] = attrs[k][ix_ele]
                next_id += 1
                visited[el.name] = el
                models.elements.append(el)
            models.beamlines[0]["items"].append(el._id)
        return models

    return _build_models()
