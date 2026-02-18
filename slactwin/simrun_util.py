"""Simrun utilities

:copyright: Copyright (c) 2025 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import datetime
import h5py
import lcls_live.datamaps
import numpy
import pandas
import pykern.pkio
import pykern.pkjson
import re
import zoneinfo

# TODO(pjm): this is temporary to get quads working
# remove 2: ("SLED Motor Not At Limit", 65) fault
del lcls_live.klystron.dsta1_fault_map[2]


class Archiver:
    def __init__(self, pv_filename, twin_name, model_name):
        year, month, day, isotime = ca_isotime_from_filename(pv_filename)
        self.twin_name = twin_name
        self.model_name = model_name
        self.isotime = isotime
        self.filename = f"{twin_name}-{model_name}-{isotime}.h5"
        self.out_path = f"{year}/{month}/{day}/{self.filename}"

    def archive_path(self, sim_dir):
        self.path = pykern.pkio.py_path(sim_dir).join(self.filename)
        return str(self.path)

    def add_summary(self, pv_summary, outputs, out_dir=None):
        # archive_path() must be called first
        assert getattr(self, "path")
        with h5py.File(str(self.path), "r+") as f:
            g = f.create_group("summary")
            g.attrs["isotime"] = self.isotime
            g.attrs["twin_name"] = self.twin_name
            g.attrs["machine_name"] = self.model_name
            o = g.create_group("outputs")
            for n, v in outputs.items():
                o.attrs[n] = v
        s = []
        for r in pv_summary:
            if isinstance(r.pv_value, list):
                for idx, v in enumerate(r.pv_value):
                    s.append(
                        r.copy().pkupdate(
                            device_pv_name=f"{r.device_pv_name}[{idx}]",
                            pv_value=r.pv_value[idx],
                        )
                    )
            else:
                s.append(r)
        pandas.DataFrame(s).to_hdf(
            self.path,
            key="/summary/pv_mapping_dataframe",
            mode="r+",
            format="table",
        )
        if out_dir:
            p = pykern.pkio.py_path(f"{out_dir}/{self.out_path}")
            pykern.pkio.mkdir_parent_only(p)
            self.path.move(p)


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


def build_commands(model_name, pvfile):
    cmds = []
    pvinfo = PKDict()
    with open(pvfile, "r") as f:
        pvdata = pykern.pkjson.load_any(f)

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
            if r[datamap.pvname] not in pvdata:
                pkdc("Missing pvdata for {}", r[datamap.pvname])
            d = PKDict(
                name=r["name"] if "name" in r else r[datamap.element],
                bmad_unit=r["bmad_unit"] if "bmad_unit" in r else "",
                pv_value=pvdata.get(r[datamap.pvname], 0),
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
        # TODO(pjm): add method argument for ignore list
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
        (
            [
                "set global lattice_calc_on = F",
                "set lattice model=design ! Reset the lattice",
                # tell bmad to evaluate using b1_gradient values
                "set ele quad::* field_master = T",
            ]
            + cmds
            + [
                "set global lattice_calc_on = T",
            ]
        ),
        pvinfo,
        pvdata,
    )


def ca_isotime_from_filename(filename):
    m = re.search(r"(\d{4}-.*?)\.json", filename)
    if not m:
        raise AssertionError(f"failed to extract isotime from filename: {filename}")
    d = to_ca_datetime(m.group(1))
    return str(d.year), str(d.month).zfill(2), str(d.day).zfill(2), d.isoformat()


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


def to_ca_datetime(isotime):
    """Convert a string in iso format to a CA timezone iso format"""
    return (
        datetime.datetime.fromisoformat(isotime)
        .replace(microsecond=0)
        .astimezone(zoneinfo.ZoneInfo("America/Los_Angeles"))
    )
