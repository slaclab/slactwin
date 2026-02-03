"""Simple Impact-T runner

:copyright: Copyright (c) 2026 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from slactwin.simrun_util import Archiver
import h5py
import matplotlib.pyplot as plt
import numpy
import os
import pmd_beamphysics
import pykern.pkjson
import re
import slactwin.simrun_util
from impact import Impact

_MODEL_NAME_TO_IMPACT_FILE = PKDict(
    cu_inj="impact/models/cu_inj/v0/ImpactT.in",
    sc_inj="impact/models/sc_inj/v2/ImpactT.in",
)

_TWIN_NAME = "impact"


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

    def _outputs(I):
        return PKDict({f"end_{c}": I.output["stats"][c][-1] for c in I.output["stats"]})

    assert "LCLS_LATTICE" in os.environ
    assert beam_in

    I = Impact(
        f"{os.environ['LCLS_LATTICE']}/{_MODEL_NAME_TO_IMPACT_FILE[model_name]}",
        # TODO(pjm): config beam_in
        initial_particles=pmd_beamphysics.ParticleGroup(beam_in),
        # TODO(pjm): remove workdir/tempdir config
        workdir="/home/vagrant/tmp/impact-tmp",
        use_temp_dir=False,
    )
    # TODO(pjm): configurable
    I.numprocs = 8
    I.header["Np"] = 1000

    I.run()

    a = Archiver(pv_filename, _TWIN_NAME, model_name)
    with h5py.File(a.archive_path(I.path), "w") as f:
        g = f.create_group(_TWIN_NAME)
        I.archive(g)
    pv_summary = []
    a.add_summary(pv_summary, _outputs(I), out_dir)
