"""Simple pytao runner

:copyright: Copyright (c) 2025 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

# TODO(pjm): rename modules from pytao to bmad

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pytao import Tao
import h5py
import json
import matplotlib.pyplot as plt
import numpy
import os
import pandas
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


def run(model_name, pv_filename, start_element_name, end_element_name, watches=""):
    # ex. slactwin simrun-pytao run cu_hxr /home/vagrant/2025-12-04.json WS02 ENDBC1 -w BC1CBEG:BC1CEND

    def evaluate_tao(tao, cmds, pvinfo):
        res = []
        ele_names = tao.lat_list("*", "ele.name", flags="-no_slaves")
        for cmd in cmds:
            n = slactwin.simrun_util.parse_element_name_from_cmd(cmd)
            if n and (n != "beginning" and n not in ele_names):
                continue
            tao.cmd(cmd)
            p = slactwin.simrun_util.parse_cmd(cmd)
            if p and p[0] in pvinfo:
                for c in pvinfo[p[0]]:
                    if c.attribute == p[1]:
                        res.append(c)
                        c.value = p[2]
        for cmd in (
            f"set beam_init track_start = {start_element_name}",
            # TODO(pjm): command line arg for particle count
            "set beam_init n_particle = 10000",
            "set global track_type = beam",
            "set global track_type = single",
        ):
            tao.cmd(cmd)
        return res

    # TODO(pjm): could pass in path to private repo
    assert "LCLS_LATTICE" in os.environ
    cmds, pvinfo = slactwin.simrun_util.build_commands(
        model_name, json.load(open(pv_filename))
    )
    tao = Tao(
        f"-init $LCLS_LATTICE/bmad/models/{model_name}/tao.init -slice {start_element_name}:{end_element_name} -noplot"
    )
    summary = evaluate_tao(tao, cmds, pvinfo)
    stats = _archive(
        tao,
        [start_element_name, end_element_name]
        + (watches.split(":") if watches else []),
    )
    _summary(tao, summary, stats, end_element_name)
    # _plot_twiss(stats)
    # plt.show()


def _summary(tao, summary, stats, end_element_name):

    # print(f"summary: {summary}")

    def _summary_outputs():
        return PKDict({f"end_{c}": stats[c][-1] for c in stats})

    summary_out = PKDict(
        # TODO(pjm): fix hard-coded
        isotime="2024-06-19T00:23:17-07:00",
        config=PKDict(
            command="pytao",
        ),
        pv_mapping_dataframe=pandas.DataFrame(summary).to_dict(),
        outputs=_summary_outputs().pkupdate(
            # TODO(pjm): fix hard-coded
            archive="/home/vagrant/src/slaclab/slactwin/out-pytao.h5",
        ),
    )
    pykern.pkjson.dump_pretty(summary_out, "summary-pytao.json")


def _archive(tao, watches):

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

    res = PKDict()
    # TODO(pjm): location/name of summary and h5 output file
    with h5py.File("out-pytao.h5", "w") as f:
        g = f.create_group("pytao")
        gs = g.create_group("stats")
        _add_element_values(res, gs)
        _add_bunch_params(res, gs)
        for idx, n in enumerate(watches):
            P = pmd_beamphysics.ParticleGroup(data=tao.bunch_data(n))
            name = (
                "initial_particles"
                if idx == 0
                else "final_particles" if idx == 1 else n
            )
            P.write(f, name=f"/pytao/particles/{name}")
        g.attrs["lattice"] = pykern.pkjson.dump_pretty(_tao_lattice(tao, watches))
    return res


# TODO(pjm): temporary for manual verification
def _plot_twiss(output):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(16, 4))
    ax.plot(output["s"], output["a.beta"], label=r"$\beta_a$")
    ax.plot(output["s"], output["b.beta"], label=r"$\beta_b$")
    plt.legend()
    # Add energy to the rhs
    ax2 = ax.twinx()
    ax2.plot(output["s"], numpy.array(output["e_tot"]) / 1e9, color="red")
    ax2.set_ylabel("Energy (GeV)")
    ax.set_xlabel("s (m)")
    ax.set_ylabel("Twiss Beta (m)")
    efinal = output["e_tot"][-1] / 1e9
    plt.title(f"Final energy: {efinal:.5f} GeV")


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
