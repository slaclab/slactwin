"""Command line utilities.

:copyright: Copyright (c) 2026 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

import h5py
from pmd_beamphysics import ParticleGroup


def extract_particles_from_archive(
    archive_file, out_file=None, particles_name="final_particles"
):
    with h5py.File(archive_file, "r") as f:
        for n in f:
            if "output" in f[n] and "particles" in f[f"{n}/output"]:
                if particles_name in f[f"{n}/output/particles"]:
                    ParticleGroup(
                        h5=f[f"/{n}/output/particles/{particles_name}"]
                    ).write(out_file or f"{particles_name}.h5")
                    return
    raise AssertionError(
        "Unable to find output particles in archive: {}", particles_name
    )
