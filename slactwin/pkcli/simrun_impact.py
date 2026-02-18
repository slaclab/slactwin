"""SLACTwin Impact-T runner

:copyright: Copyright (c) 2026 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from impact import Impact
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template.code_variable import PurePythonEval
from slactwin.simrun_util import Archiver
import h5py
import matplotlib.pyplot as plt
import numpy
import os
import pmd_beamphysics
import pykern.pkjson
import re
import slactwin.simrun_util

_MODEL_NAME_TO_IMPACT_FILE = PKDict(
    cu_inj="impact/models/cu_inj/v0/ImpactT.yaml",
    sc_inj="impact/models/sc_inj/v1/ImpactT.yaml",
)

_TWIN_NAME = "impact"


def run(
    model_name,
    pv_filename,
    start_element_name,
    end_element_name,
    # TODO(pjm): constrain watches
    watches="",
    beam_in=None,
    work_dir=None,
    out_dir=None,
):
    """
    Run an Impact-T simulation between two lattice elements.

    This function executes a beam dynamics simulation for the specified
    model using process variable (PV) settings provided in a JSON file.

    Example:
        slactwin simrun-impact run sc_inj sc_inj-2024-06-19T05:23:19-07:00.json \
            BEGINNING BEAM0 --beam-in sc_inj-initial-particles.h5 \
            --watches YAG01B:CM01BEG

    Args:
        model_name (str):
            Name of the accelerator model to use (e.g., "cu_inj", "sc_inj").

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
    _DESC = PKDict(
        field_autoscale="Voltage",
        phi0="Phase",
        b1_gradient="Gradient",
    )
    _FIELD = PKDict(
        field_autoscale="rf_field_scale",
        bs_field="solenoid_field_scale",
        phi0="autophase_deg",
    )
    _GROUP = PKDict(
        phi0="dtheta0_deg",
        voltage="voltage",
    )

    def _map_summary_fields(summary):
        return summary.pkupdate(
            Variable=f'{summary.element} {_DESC.get(summary.attribute, "")}',
            impact_value=summary.value,
            impact_name=f"{summary.element}:{_FIELD.get(summary.attribute, summary.attribute)}",
            # TODO(pjm): ask Impact instance for field units
            impact_unit="",
            impact_factor=summary.factor,
        )

    def _outputs(I):
        return PKDict({f"end_{c}": I.output["stats"][c][-1] for c in I.output["stats"]})

    if start_element_name != "BEGINNING":
        # TODO(pjm): if need to start from a different element, need to shift all elements
        # so the first element is at position 0
        raise AssertionError("Impact-T first element must be BEGINNING")
    assert "LCLS_LATTICE" in os.environ
    I = Impact.from_yaml(
        f"{os.environ['LCLS_LATTICE']}/{_MODEL_NAME_TO_IMPACT_FILE[model_name]}"
    )
    # TODO(pjm): remove workdir/tempdir config
    I._use_temp_dir = False
    I.workdir = "/home/vagrant/tmp/impact-tmp"
    if beam_in:
        I.initial_particles = pmd_beamphysics.ParticleGroup(beam_in)
    # TODO(pjm): configurable
    I.numprocs = 16

    I.stop = I.ele[end_element_name]["s"] + I.ele[end_element_name].get("L", 0)

    code_var = PurePythonEval()

    def eval_expression(expression):
        v, e = code_var.eval_var(expression, [], {})
        assert not e, f"invalid expression: {expression}, err: {e}"
        return v

    tao_cmds, pvinfo, pvdata = slactwin.simrun_util.build_commands(
        "cu_spec" if model_name == "cu_inj" else model_name, pv_filename
    )

    # TODO(pjm): charge from beam_in or from PV?
    if model_name == "sc_inj":
        I.total_charge = pvdata["BPMS:GUNB:314:TMIT"] * 1.6e-7 * 1e-12
    elif model_name == "cu_inj":
        I.total_charge = pvdata["BPMS:IN20:221:TMIT"] * 1.6e-7 * 1e-12

    # TODO(pjm): for testing only
    # I.total_charge = 0

    if beam_in and I.total_charge:
        # TODO(pjm): should respect the initial charge from particles?
        I.initial_particles.charge = I.total_charge

    # TODO(pjm): constant values from inputs
    if model_name == "sc_inj":
        tao_cmds += [
            "set ele RFGUNB field_autoscale = 16486924.441375",
            "set ele RFGUNB phi0 = 0",
            "set ele BUN1B field_autoscale = 1786301.125",
            # TODO(pjm): don't assume conversion value
            "set ele BUN1B phi0 = 0.0027777778 * -57",
        ]
    pv_summary = []
    groups = PKDict()
    for n in I.group:
        g, f = re.search(r"^(.*?)\_(.*)$", n).groups()
        if g in groups:
            groups[g][f] = n
        else:
            groups[g] = PKDict({f: n})

    def pvinfo_for_command(cmd):
        if cmd[0] in groups:
            p = [v for v in pvinfo[cmd[0]] if v.attribute == cmd[1]]
        else:
            p = pvinfo[cmd[0]]
        assert len(p) == 1
        return p[0]

    for cmd_str in tao_cmds:
        cmd = slactwin.simrun_util.parse_cmd(cmd_str)
        if not cmd:
            continue

        if cmd[0] in groups:
            p = pvinfo_for_command(cmd)
            if cmd[1] == "phi0":
                n = groups[cmd[0]].phase
                I[n]["dtheta0_deg"] = eval_expression(cmd[2]) / 0.0027777778
                p.element = n
                p.attribute = "dtheta0_deg"
                cmd[1] = p.attribute
                p.value = str(p.pv_value)
                p.factor = 1
            elif cmd[1] == "voltage":
                n = groups[cmd[0]].scale
                I[n]["voltage"] = eval_expression(cmd[2])
                p.element = n
                p.value = str(I[n]["voltage"])
            else:
                assert False
        elif cmd[0] not in I.ele:
            continue
        # TODO(pjm): use bmad-->impact-t field mapping
        elif cmd[1] == "phi0":
            # TODO(pjm): remove bmad scaling from expression instead of dividing
            # v = eval_expression(cmd[2]) / 0.0027777778
            p = pvinfo_for_command(cmd)
            v = p.pv_value
            I[f"{cmd[0]}:autophase_deg"] = v
            p.value = str(v)
            p.factor = 1
        elif cmd[1] == "field_autoscale":
            v = eval_expression(cmd[2])
            I.ele[cmd[0]]["rf_field_scale"] = v
            pvinfo_for_command(cmd).value = str(v)
        elif cmd[1] == "b1_gradient":
            v = eval_expression(cmd[2])
            I.ele[cmd[0]]["b1_gradient"] = v
            pvinfo_for_command(cmd).value = str(v)
        elif cmd[1] == "bs_field":
            p = pvinfo_for_command(cmd)
            if cmd[0] == "SOL1":
                # TODO(pjm): lcls-live factor for SOL1.bs_field is incorrect?
                p.factor = 0.51427242
                v = p.pv_value * p.factor
            else:
                v = eval_expression(cmd[2])
            I.ele[cmd[0]]["solenoid_field_scale"] = v
            p.value = str(v)
        elif cmd[1] == "k1l":
            p = pvinfo_for_command(cmd)
            p.factor = -0.1 / I.ele[cmd[0]]["L_effective"]
            v = p.factor * p.pv_value
            I.ele[cmd[0]]["b1_gradient"] = v
            p.attribute = "b1_gradient"
            cmd[1] = p.attribute
            p.value = str(v)
        else:
            assert False
        if cmd[0] not in pvinfo:
            continue
        for v in pvinfo[cmd[0]]:
            if v.attribute == cmd[1]:
                # v.value = cmd[2]
                # if 'value' not in v:
                #     v.value = cmd[2]
                pv_summary.append(_map_summary_fields(v))

    I.run()

    a = Archiver(pv_filename, _TWIN_NAME, model_name)
    with h5py.File(a.archive_path(I.path), "w") as f:
        g = f.create_group(_TWIN_NAME)
        I.archive(g)
    a.add_summary(pv_summary, _outputs(I), out_dir)
