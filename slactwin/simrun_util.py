"""Simrun utilities

:copyright: Copyright (c) 2025 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkdebug import pkdc, pkdlog, pkdp
import lcls_live.datamaps
import numpy
import re

# TODO(pjm): this is temporary to get quads working
# remove 2: ("SLED Motor Not At Limit", 65) fault
del lcls_live.klystron.dsta1_fault_map[2]


def beta_gamma_to_energy_gev(mass, values):
    # TODO(pjm): simplify
    pc = numpy.array(values) * mass
    r2 = pc**2 / (mass**2)
    beta = numpy.sqrt(r2 / (1 + r2))
    gamma = 1 / numpy.sqrt(1 - beta**2)
    energy = gamma * mass
    return energy * 1e-3


def beta_gamma_to_pc(mass, values):
    return values * mass


def build_commands(model_name, pvdata):
    cmds = []
    for dn, dm in lcls_live.datamaps.get_datamaps(model_name).items():
        if dn in ("bpms", "correctors"):
            continue
        cmds += dm.as_tao(pvdata)
    return (
        [
            "place floor energy",
            "set global lattice_calc_on = F",
            "set lattice model=design ! Reset the lattice",
            "set ele quad::* field_master = T",
        ]
        + cmds
        + [
            "set global lattice_calc_on = T",
        ]
    )


def parse_element_name_from_cmd(cmd_str):
    m = re.match(r"^set ele (\w+)\s(.*?)\s=\s(.*?)$", cmd_str)
    return m.group(1) if m else None


def parse_cmd(cmd_str):
    if (
        not cmd_str
        or cmd_str.startswith("#")
        or cmd_str.startswith("!")
        or " data " in cmd_str
    ):
        return None
    m = re.match(r"set ele (\w+?)\s(.*?)\s=\s(.*?)$", cmd_str)
    return [m.group(1), m.group(2), m.group(3)] if m else None
