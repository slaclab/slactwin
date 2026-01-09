"""Simrun utilities

:copyright: Copyright (c) 2025 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import datetime
import lcls_live.datamaps
import numpy
import re
import zoneinfo

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
    pvinfo = PKDict()

    def _add_pvinfo(record):
        if record["element"] not in pvinfo:
            pvinfo[record["element"]] = []
        if "factor" not in record:
            record["factor"] = 1
        pvinfo[record["element"]].append(record)

    def _klystron_summary(datamap):
        n = datamap.bmad_name
        for idx, pv in enumerate(datamap.pvlist):
            _add_pvinfo(
                PKDict(
                    name=n,
                    bmad_unit="",
                    pv_value=pvdata[pv],
                    element=n,
                    attribute=(
                        "ENLD_MeV"
                        if idx == 0
                        else "phase_deg" if idx == 1 else "in_use"
                    ),
                    device_pv_name=pv,
                    factor=1,
                )
            )

    def _tabular_summary(datamap):
        for idx, r in datamap.data.iterrows():
            d = PKDict(
                name=r["name"] if "name" in r else r[datamap.element],
                bmad_unit=r["bmad_unit"] if "bmad_unit" in r else "",
                pv_value=pvdata[r[datamap.pvname]],
            )
            for f in (
                "element",
                "attribute",
                "pvname",
                "factor",
            ):
                if getattr(datamap, f):
                    d["device_pv_name" if f == "pvname" else f] = r[getattr(datamap, f)]
            _add_pvinfo(d)

    for dn, dm in lcls_live.datamaps.get_datamaps(model_name).items():
        if dn in ("bpms", "correctors"):
            continue
        if isinstance(dm, lcls_live.datamaps.TabularDataMap):
            _tabular_summary(dm)
        elif isinstance(dm, lcls_live.datamaps.KlystronDataMap):
            _klystron_summary(dm)
        else:
            raise AssertionError(f"Unhandled datamap class: {dm}")
        cmds += dm.as_tao(pvdata)

    return (
        [
            "place floor energy",
            "set global lattice_calc_on = F",
            "set lattice model=design ! Reset the lattice",
            # tell bmad to evaluate using b1_gradient values
            "set ele quad::* field_master = T",
        ]
        + cmds
        + [
            "set global lattice_calc_on = T",
        ]
    ), pvinfo


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


def to_ca_isotime(isotime):
    """Convert a string in iso format to a CA timezone iso format"""
    return (
        datetime.datetime.fromisoformat(isotime)
        .replace(microsecond=0)
        .astimezone(zoneinfo.ZoneInfo("America/Los_Angeles"))
        .isoformat()
    )
