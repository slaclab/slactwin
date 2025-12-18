"""Simple pytao runner

:copyright: Copyright (c) 2025 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkdebug import pkdc, pkdlog, pkdp
from pytao import Tao
import json
import os
import pmd_beamphysics
import slactwin.simrun_util


def run(model_name, pv_filename, start_element_name, end_element_name, watches=""):
    # ex. slactwin simrun-pytao run cu_hxr /home/vagrant/2025-12-04.json WS02 ENDBC1 -w BC1CBEG:BC1CEND

    def evaluate_tao(tao, cmds):
        ele_names = tao.lat_list("*", "ele.name", flags="-no_slaves")
        for cmd in cmds:
            n = slactwin.simrun_util.parse_element_name_from_cmd(cmd)
            if n and (n != "beginning" and n not in ele_names):
                continue
            tao.cmd(cmd)
        tao.cmd(f"set beam_init track_start = {start_element_name}")
        # TODO(pjm): command line arg for particle count
        tao.cmd("set beam_init n_particle = 10000")
        tao.cmd("set global track_type = beam")
        tao.cmd("set global track_type = single")
        return {
            k: tao.lat_list("*", f"ele.{k}")
            # TODO(pjm): archive off all computed and particle values
            for k in ["s", "e_tot", "a.beta", "b.beta", "a.alpha", "b.alpha"]
        }

    # TODO(pjm): could pass in path to private repo
    assert "LCLS_LATTICE" in os.environ
    cmds, pvinfo = slactwin.simrun_util.build_commands(
        model_name, json.load(open(pv_filename))
    )
    tao = Tao(
        f"-init $LCLS_LATTICE/bmad/models/{model_name}/tao.init -slice {start_element_name}:{end_element_name} -noplot"
    )
    o = evaluate_tao(tao, cmds)

    for name in [start_element_name, end_element_name] + watches.split(":"):
        P = pmd_beamphysics.ParticleGroup(data=tao.bunch_data(name))
        if name == end_element_name:
            P.plot("delta_t", "delta_energy")
        else:
            P.plot("x", "y")
        P.write(f"{name}.h5")

    _plot_twiss(o)


# TODO(pjm): temporary for manual verification
def _plot_twiss(output):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(16, 4))
    ax.plot(output["s"], output["a.beta"], label=r"$\beta_a$")
    ax.plot(output["s"], output["b.beta"], label=r"$\beta_b$")
    plt.legend()
    # Add energy to the rhs
    ax2 = ax.twinx()
    ax2.plot(output["s"], output["e_tot"] / 1e9, color="red")
    ax2.set_ylabel("Energy (GeV)")
    ax.set_xlabel("s (m)")
    ax.set_ylabel("Twiss Beta (m)")
    efinal = output["e_tot"][-1] / 1e9
    plt.title(f"Final energy: {efinal:.5f} GeV")
    plt.show()
