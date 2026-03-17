"""SLACTwin Impact-T runner

:copyright: Copyright (c) 2026 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from impact import Impact
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from slactwin.simrun_util import Archiver
import h5py
import os
import pmd_beamphysics
import pykern.pkjson
import slactwin.datamaps.impact
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
    # I.verbose = True
    if work_dir:
        I._use_temp_dir = False
        I.workdir = work_dir
    if beam_in:
        I.initial_particles = pmd_beamphysics.ParticleGroup(beam_in)
    # TODO(pjm): configurable
    I.numprocs = 16

    I.stop = I.ele[end_element_name]["s"] + I.ele[end_element_name].get("L", 0)

    with open(pv_filename, "r") as f:
        pvdata = pykern.pkjson.load_any(f)

    pv_summary = []
    for name, dm in slactwin.datamaps.impact.get_impact_datamaps(model_name).items():
        for idx, r in dm.data.iterrows():
            if "pvname_rbv" in r:
                # use the RBV pv if present
                r.pvname = r.pvname_rbv
            if r.pvname not in pvdata:
                pkdc("missing pv {}", r.pvname)
                continue
            pv_summary.append(
                PKDict(
                    Variable=f'{r.impact_name} {_DESC.get(r.impact_attribute, "")}',
                    device_pv_name=r.pvname,
                    pv_value=pvdata[r.pvname],
                    impact_name=slactwin.datamaps.impact.impact_field_name(
                        r.impact_name, r.impact_attribute
                    ),
                    impact_unit=r.impact_unit,
                    impact_factor=r.impact_factor,
                )
            )
        for f, v in slactwin.datamaps.impact.as_impact(dm, pvdata).items():
            for r in pv_summary:
                if f == r.impact_name:
                    pkdc("set {} = {}", f, v)
                    I[f] = v
                    r.impact_value = v
        pv_summary = [r for r in pv_summary if "impact_value" in r]

    if model_name == "sc_inj":
        # TODO(pjm): allow setting overrides from input arguments
        I["RFGUNB:rf_field_scale"] = 16486924.441375
        I["RFGUNB:autophase_deg"] = 0
        I["BUN1B:rf_field_scale"] = 1786301.125
        I["BUN1B:autophase_deg"] = -57

    # TODO(pjm): for testing only, runs faster
    # I.total_charge = 0

    if beam_in and I.total_charge:
        # TODO(pjm): should respect the initial charge from input particles?
        I.initial_particles.charge = I.total_charge

    I.run()

    a = Archiver(pv_filename, _TWIN_NAME, model_name)
    with h5py.File(a.archive_path(I.path), "w") as f:
        I.archive(f.create_group(_TWIN_NAME))
    a.add_summary(pv_summary, _outputs(I), out_dir)
