"""Simple elegant runner

:copyright: Copyright (c) 2025 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pmd_beamphysics import ParticleGroup
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from rslume.elegant import Elegant
from scipy.interpolate import Akima1DInterpolator
from sirepo.template.code_variable import PurePythonEval
from slactwin.simrun_util import Archiver
import copy
import functools
import glob
import json
import math
import matplotlib
import matplotlib.pyplot as plt
import os
import pmd_beamphysics
import pykern.pkio
import pykern.pkjson
import pykern.pkresource
import slactwin.simrun_util

# TODO(pjm): move calc to util
meV = 0.51099906

_MODEL_NAME_TO_ELEGANT_FILE = PKDict(
    cu_hxr="elegant/models/LCLS2cu/LCLS2cuH.ele",
)

_TWIN_NAME = "elegant"


def run(
    model_name,
    pv_filename,
    start_element_name,
    end_element_name,
    watches="",
    beam_in=None,
    work_dir=None,
    out_dir=None,
):
    # ex. slactwin simrun-elegant run cu_hxr /home/vagrant/2025-12-04.json WS02 ENDBC1 -w BC1CBEG:BC1CEND

    def _add_variables(e, defaults):
        for n, v in defaults.vars.items():
            e._input.models.rpnVariables.append(
                PKDict(
                    name=n,
                    value=v,
                )
            )

    def _element_name_set(e, el_map):
        res = set()
        for el_id in e._input.models.beamlines[0]["items"]:
            el = el_map[el_id]
            res.add(el.name)
        return res

    def _var_in_use(e, name, el_map):
        for el_id in e._input.models.beamlines[0]["items"]:
            el = el_map[el_id]
            if el.type != "RFCW":
                continue
            for f in ("volt", "phase"):
                if name in el[f]:
                    return True
        return False

    def _prepare_elegant_input_files(path):
        # rslume-elegant requires all input files in one directory
        for n in ("wakefields", "beams"):
            for f in glob.glob(str(path.join("../..", n)) + "/*.*"):
                s = pykern.pkio.py_path(f)
                t = path.join(s.basename)
                if not t.exists():
                    t.mksymlinkto(s, absolute=False)

        w = None
        if work_dir:
            w = pykern.pkio.py_path(work_dir)
            if w.isdir() and w.listdir():
                raise AssertionError(f"work_dir contains files: {w}")
            pykern.pkio.unchecked_remove(work_dir)
            pykern.pkio.mkdir_parent(work_dir)
        if beam_in:
            b = path.join(pykern.pkio.py_path(beam_in).basename + ".ssds")
            pmd_beamphysics.interfaces.elegant.write_elegant(
                ParticleGroup(beam_in),
                str(b),
            )
            return w, b.basename
        return w, None

    def _outputs(e):
        return PKDict({f"end_{c}": e.output.stats[c][-1] for c in e.output.stats})

    def _update_fields(e, defaults):
        for el in e._input.models.elements:
            if el.name in defaults.fields:
                el.pkupdate(defaults.fields[el.name])

    defaults = _elegant_defaults(model_name)
    elegant_in = pykern.pkio.py_path(
        f"{os.environ['LCLS_LATTICE']}/{_MODEL_NAME_TO_ELEGANT_FILE[model_name]}"
    )
    work_dir, beam_in = _prepare_elegant_input_files(elegant_in.dirpath())
    e = Elegant(
        elegant_in,
        workdir=work_dir,
        use_temp_dir=not bool(work_dir),
    )
    el_map = _unique_klystrons(e, defaults)
    e.fix_deprecated_elements()
    _update_fields(e, defaults)
    e.slice(start_element_name, end_element_name)
    e.set_watches(watches.split(":"))

    el_names = _element_name_set(e, el_map)

    # TODO(pjm): command-line arg for overrides
    # override to real value here, not approx 135 from actual sim
    e.cmd("run_setup").p_central_mev = 134.9990329

    if beam_in:
        e.cmd("sdds_beam").pkupdate(
            input=beam_in,
            sample_interval=1,
        )

    # TODO(pjm): only needed when testing the design lattice (no pvdata updates)
    # design twiss, different than elegant simulation default
    e.cmd("twiss_output").pkupdate(
        dict(
            beta_x=1.11011741290,
            alpha_x=0.06877052527316094,
            beta_y=1.1550350841830834,
            alpha_y=0.13564743199080678,
        )
    )

    code_var = PurePythonEval()

    def eval_expression(expression):
        v, e = code_var.eval_var(expression, [], {})
        assert not e, f"invalid expression: {expression}, err: {e}"
        return v

    tao_cmds, pvinfo = slactwin.simrun_util.build_commands(
        model_name, json.load(open(pv_filename))
    )
    pv_summary = []

    # TODO(pjm): separate into another method
    # first run to get energies so quad gradients can be computed
    for cmd_str in tao_cmds:
        cmd = slactwin.simrun_util.parse_cmd(cmd_str)
        if not cmd or cmd[1] == "b1_gradient":
            continue
        if cmd[0] == "beginning":
            m = PKDict(
                beta_a="beta_x",
                beta_b="beta_y",
                alpha_a="alpha_x",
                alpha_b="alpha_y",
            )
            e.cmd("twiss_output").pkupdate(
                {
                    m[cmd[1]]: cmd[2],
                }
            )
            if cmd[0] in pvinfo:
                for c in pvinfo[cmd[0]]:
                    if c.attribute == cmd[1]:
                        pv_summary.append(c)
                        c.value = str(cmd[2])
            continue
        if cmd[0] in defaults.overlays:
            v = _apply_overlay(e, eval_expression(cmd[2]), defaults.overlays[cmd[0]])
            if cmd[0] in pvinfo and defaults.overlays[cmd[0]].bend_names[0] in el_names:
                assert len(pvinfo[cmd[0]]) == 1
                p = pvinfo[cmd[0]][0]
                p.pkupdate(value=str(v), factor=v / p.pv_value if p.pv_value else 0),
                pv_summary += pvinfo[cmd[0]]

        n = f"{cmd[0]}_{cmd[1]}"
        if n in defaults.vars:
            defaults.vars[n] = cmd[2]
            if cmd[0] in pvinfo and _var_in_use(e, n, el_map):
                for c in pvinfo[cmd[0]]:
                    if c.attribute in n:
                        c.value = str(cmd[2])
                        pv_summary.append(c)

    _add_variables(e, defaults)

    m = _build_element_energy_map(e)
    SPEED_OF_LIGHT = 299792458  # [m/s]
    eCharge = -1

    # update quad K1, computed from energy and gradient
    for cmd_str in tao_cmds:
        cmd = slactwin.simrun_util.parse_cmd(cmd_str)
        if not cmd or cmd[1] != "b1_gradient":
            continue
        if cmd[0] not in m:
            continue
        # compute K1
        el = e.el(cmd[0])
        pc = m[cmd[0]] * meV
        Bp = pc * 1e-3 / (SPEED_OF_LIGHT * 1e-9)
        k1 = eval_expression(cmd[2]) / Bp * eCharge
        el.k1 = k1
        if cmd[0] in pvinfo and cmd[0] in el_names:
            assert len(pvinfo[cmd[0]]) == 1
            pvinfo[cmd[0]][0].value = str(k1)
            pv_summary += pvinfo[cmd[0]]

    if work_dir:
        pykern.pkio.unchecked_remove(work_dir)
        pykern.pkio.mkdir_parent(work_dir)
    else:
        e.reset()
    e.run()
    a = Archiver(pv_filename, _TWIN_NAME, model_name)
    e.archive(a.archive_path(e.path))
    a.add_summary(pv_summary, _outputs(e), out_dir)
    # _plot_twiss(e)


def _apply_overlay(E, value, config):
    # TODO(pjm): assumes knot overlay
    angle_deg = Akima1DInterpolator(config.knot_range, config.knot_value)(value).item()
    theta = angle_deg * math.pi / 180
    assert len(config.bend_names) == 4
    for n in config.bend_names:
        sign = 1 if n in (config.bend_names[0], config.bend_names[3]) else -1
        e = E.el(n)
        e.l = config.Lp * sign * theta / math.sin(sign * theta)
        assert e.l > 0
        e.angle = sign * theta
        e["e2" if n in (config.bend_names[0], config.bend_names[2]) else "e1"] = (
            sign * theta
        )
    for n in config.drift_names:
        E.el(n).l += config.Lp_drift * (
            1 / math.cos(theta) - 1 / math.cos(config.bc_theta_default)
        )
    return angle_deg


def _build_element_energy_map(e):
    e.run_twiss_only()
    energies = PKDict(
        {
            n: e.output.stats[n]
            for n in ("pCentral0", "ElementName", "ElementOccurence", "ElementType")
        }
    )
    r = PKDict()
    for idx in range(len(energies.pCentral0)):
        n = energies.ElementName[idx]
        en = energies.pCentral0[idx]
        if n in r:
            if not energies.ElementType[idx] in (
                "RFCW",
                "RFDF",
                "LSCDRIFT",
            ):
                assert (
                    r[n] == en
                ), f"Element {energies.ElementType[idx]}: {n} present at multiple energies"
            continue
        r[n] = en
    return r


def _elegant_defaults(model_name):
    with open(pykern.pkresource.file_path(f"{model_name}-elegant.json"), "r") as f:
        defaults = pykern.pkjson.load_any(f)
    # TODO(pjm): generate from ipynb in LCLS_LATTICE, store in elegant.json
    defaults.overlays = PKDict(
        O_BC1_OFFSET=PKDict(
            knot_range=[
                -2.00000000e-01,
                -1.33333333e-01,
                -6.66666667e-02,
                2.77555756e-17,
                6.66666667e-02,
                1.33333333e-01,
                2.00000000e-01,
                2.66666667e-01,
                3.33333333e-01,
                4.00000000e-01,
            ],
            knot_value=[
                4.33589907,
                2.89349031,
                1.44761486,
                0.0,
                -1.44761486,
                -2.89349031,
                -4.33589907,
                -5.77313792,
                -7.20353921,
                -8.6254818,
            ],
            Lp=0.2032,
            Lp_drift=2.4349,
            bc_theta_default=-0.093575352547,
            bend_names=("BX11", "BX12", "BX13", "BX14"),
            # D21oA D21oB
            drift_names=("CS000016", "CS000021"),
        ),
        O_BC2_OFFSET=PKDict(
            knot_range=[
                -0.2,
                -0.13333333,
                -0.06666667,
                0.0,
                0.06666667,
                0.13333333,
                0.2,
                0.26666667,
                0.33333333,
                0.4,
                0.46666667,
                0.53333333,
                0.6,
            ],
            knot_value=[
                1.10073799,
                0.7338735,
                0.3669512,
                0.0,
                -0.3669512,
                -0.7338735,
                -1.10073799,
                -1.4675158,
                -1.8341781,
                -2.20069612,
                -2.56704115,
                -2.93318456,
                -3.29909781,
            ],
            Lp=0.549,
            Lp_drift=9.8602,
            bc_theta_default=-0.036971268085,
            bend_names=("BX21", "BX22", "BX23", "BX24"),
            # D21oA D21oB
            drift_names=("CS000032", "CS000039"),
        ),
    )
    return defaults


# TODO(pjm): temporary for manual verification
def _plot_twiss(e):

    def _plot_sdds(e, x_column, y_columns, labels, right_columns=None, conversion=None):
        def column(name):
            v = e.output.stats[name]
            if conversion and name in conversion:
                return conversion[name](v)
            return v

        fig, ax = plt.subplots(figsize=(16, 4))
        for y in y_columns:
            ax.plot(column(x_column), column(y), label=labels[y])
        plt.legend()
        if right_columns:
            matplotlib.rcParams["axes.prop_cycle"] = matplotlib.cycler(
                color=["orangered", "limegreen", "royalblue"]
            )
            ax2 = ax.twinx()
            for y in right_columns:
                ax2.plot(column(x_column), column(y), label=labels[y])
            ax2.set_ylabel(labels["y2"])
        ax.set_xlabel(labels["x"])
        ax.set_ylabel(labels["y"])
        plt.title(labels["title"])

    def plot_title(e):
        e = slactwin.simrun_util.beta_gamma_to_energy_gev(
            meV,
            e.output.stats.pCentral0,
        )[-1]
        return f"Final energy: {e:.5f} GeV"

    _plot_sdds(
        e,
        "s",
        ["betax", "betay"],
        right_columns=["pCentral0"],
        labels=dict(
            betax=r"$\beta_x$",
            betay=r"$\beta_y$",
            x="s (m)",
            y="Twiss Beta (m)",
            y2="Energy (GeV)",
            pCentral0="Energy (GeV)",
            title=plot_title(e),
        ),
        conversion=dict(
            pCentral0=functools.partial(
                slactwin.simrun_util.beta_gamma_to_energy_gev, meV
            ),
        ),
    )
    plt.show()


def _unique_klystrons(e, defaults):
    """Rename klystron (RFCW) elements to match bmad names (not elegant names)"""
    next_id = e.max_id() + 1
    bl = []
    l1x_id = None
    res = PKDict()
    for el_id in e._input.models.beamlines[0]["items"]:
        el = e.el_for_id(el_id)
        if el.type != "RFCW":
            bl.append(el_id)
            res[el_id] = el
            continue
        if l1x_id:
            bl.append(l1x_id)
            l1x_id = None
            continue
        assert len(defaults.klystrons), f"ran out of klystrons: {el._id}: {el.name}"
        n = defaults.klystrons.pop(0)
        new_el = copy.copy(el)
        new_el._id = next_id
        next_id += 1
        new_el.name = n
        e._input.models.elements.append(new_el)
        bl.append(new_el._id)
        res[new_el._id] = new_el
        if n == "L1X":
            # L1X is split in 2 for elegant
            l1x_id = new_el._id
    e._input.models.beamlines[0]["items"] = bl
    assert len(defaults.klystrons) == 0, f"leftover RFCW names: {defaults.klystrons}"
    return res
