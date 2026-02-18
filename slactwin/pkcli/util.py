"""Command line utilities.

:copyright: Copyright (c) 2026 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from math import sqrt
from pmd_beamphysics import ParticleGroup
from pykern.pkcollections import PKDict
from pytao import Tao
from scipy import optimize
import h5py
import numpy
import os
import pykern.pkjson


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


def generate_elegant_klystrons_and_compressors():
    # generate the cu_hxr-elegant.json input file to pkcli.simrun_elegant
    d = PKDict(
        vars=PKDict(),
        fields=PKDict(),
    )
    _generate_elegant_klystrons(d)
    _generate_elegant_compressors(d)
    return pykern.pkjson.dump_pretty(d)


def _generate_elegant_compressors(elegant):

    # method from lcls-lattice:bmad/overlays/cu/source/bunch_compressors.ipynb
    def theta_for_chicane(x, Lbp, Ldp):
        f = lambda theta: -2 * Lbp * numpy.tan(theta / 2) - Ldp * numpy.tan(theta) - x
        sol = optimize.root_scalar(f, bracket=[-1, 1], method="brentq")
        return sol.root

    def chicane(
        xlist, Lp_default, Lp_drift_default, offset_default, bend_names, drift_names
    ):
        return PKDict(
            knot_range=xlist.tolist(),
            knot_value=(
                numpy.array(
                    [theta_for_chicane(x, Lp_default, Lp_drift_default) for x in xlist]
                )
                * 180
                / numpy.pi
            ).tolist(),
            Lp=Lp_default,
            Lp_drift=Lp_drift_default,
            bc_theta_default=theta_for_chicane(
                offset_default, Lp_default, Lp_drift_default
            ),
            bend_names=bend_names,
            drift_names=drift_names,
        )

    elegant.overlays = PKDict(
        O_BC1_OFFSET=chicane(
            numpy.linspace(-0.2, 0.4, 10),
            0.2032,
            2.4349,
            2.47542378e-01,
            ("BX11", "BX12", "BX13", "BX14"),
            # D21oA D21oB
            ("CS000016", "CS000021"),
        ),
        O_BC2_OFFSET=chicane(
            numpy.linspace(-0.2, 0.6, 13),
            0.549,
            9.8602,
            3.85010405e-01,
            ("BX21", "BX22", "BX23", "BX24"),
            # D21oA D21oB
            ("CS000032", "CS000039"),
        ),
    )


def _generate_elegant_klystrons(elegant):
    # methods from lcls-lattice:bmad/overlays/cu/source/klystron_overlays.ipynb

    M = Tao("-init $LCLS_LATTICE/bmad/models/cu_linac/tao.init -noplot")
    NAMES = M.lat_list("*", "ele.name", flags="-no_slaves")
    ix_of = dict((n, i) for i, n in enumerate(M.lat_ele_list()))
    s_of = {}
    for n, s in zip(NAMES, M.lat_list("*", "ele.s", flags="-array_out -no_slaves")):
        s_of[n] = s
    CAVS = [name for name in NAMES if name.startswith("K") and ("#" not in name)]
    KLYS = {}
    for cav in CAVS:
        name, section = cav[0:-1], cav[-1:]
        if name not in KLYS:
            KLYS[name] = []
        KLYS[name].append(section)

    def eles_in(sector, station):
        name = f"K{sector}_{station}"
        sections = KLYS[name]
        return [name + s for s in sections]

    # Get all parameters for cavities
    CAVDAT = {}
    for name in CAVS + ["L1X"]:
        CAVDAT[name] = M.ele_gen_attribs(ix_of[name])

    def voltage_factors(sections):
        POWER_FACTOR = {
            ("A", "B", "C", "D"): (0.25, 0.25, 0.25, 0.25),
            ("B", "C", "D"): (0.5, 0.25, 0.25),
            ("A", "C", "D"): (0.5, 0.25, 0.25),
            ("A", "B", "C"): (0.25, 0.25, 0.5),
            ("A", "B", "D"): (0.25, 0.25, 0.5),
        }
        vfactors = [sqrt(p) for p in POWER_FACTOR[tuple(sections)]]
        vtot = sum(vfactors)
        return [v / vtot for v in vfactors]

    def klys_data(name, sections):
        eles = [name + s for s in sections]
        voltages = [CAVDAT[ele]["VOLTAGE"] for ele in eles]
        phi0s = [CAVDAT[ele]["PHI0"] for ele in eles]
        lengths = [CAVDAT[ele]["L"] for ele in eles]

        # Error checking
        assert len(set(phi0s)) == 1, "phi0 are not unique"
        phi0 = phi0s[0]

        vtot = sum(voltages)
        vfactors = voltage_factors(sections)
        # Overlay stuff
        oname = name

        for ele, vf, l in zip(eles, vfactors, lengths):
            elegant["fields"][ele] = dict(
                volt=f"{oname}_in_use * {oname}_ENLD_MeV * 1e6 * {vf}"
            )

        for ele in eles:
            elegant["fields"][ele]["phase"] = f"{oname}_phase_deg + 90"

        elegant["vars"][f"{oname}_in_use"] = 1
        elegant["vars"][f"{oname}_ENLD_MeV"] = vtot * 1e-6
        elegant["vars"][f"{oname}_phase_deg"] = 0

    L1X_VOLTAGE = CAVDAT["L1X"]["VOLTAGE"]
    L1X_PHI0 = CAVDAT["L1X"]["PHI0"]
    elegant["fields"]["L1X"] = dict(
        # note: the elegant L1X is split in half, requiring the /2
        volt="K21_2_in_use * K21_2_ENLD_MeV * 1e6 / 2",
        phase="K21_2_phase_deg + 90",
    )
    elegant["vars"]["K21_2_in_use"] = 1
    elegant["vars"]["K21_2_ENLD_MeV"] = L1X_VOLTAGE * 1e-6
    elegant["vars"]["K21_2_phase_deg"] = round(L1X_PHI0 * 360, 9)

    for k, v in KLYS.items():
        klys_data(k, v)

    def linac_of(name):
        s = s_of[name]
        if s_of["BEGL1"] <= s <= s_of["ENDL1"]:
            return "L1"
        elif s_of["BEGL2"] <= s <= s_of["ENDL2"]:
            return "L2"
        elif s_of["BEGL3"] <= s <= s_of["ENDL3"]:
            return "L3"
        raise AssertionError(f"unknown linac for name: {name}")

    # Collect elements
    LINAC = {"L1": [], "L2": [], "L3": []}
    for n in CAVS:
        l = linac_of(n)
        LINAC[l].append(n)

    # Find special feedback cavities
    L2FEEDBACK = []
    L2FORPHASE = []
    for n in LINAC["L2"]:
        if any([n.startswith(x) for x in ["K24_1", "K24_2", "K24_3"]]):
            L2FEEDBACK.append(n)
        else:
            L2FORPHASE.append(n)

    L3FEEDBACK = []
    L3FORPHASE = []
    for n in LINAC["L3"]:
        if any([n.startswith(x) for x in ["K29", "K30"]]):
            L3FEEDBACK.append(n)
        else:
            L3FORPHASE.append(n)
            len(L3FEEDBACK), len(L3FORPHASE)

    def unique_param(eles, param):
        p = set()
        for ele in eles:
            p.add(CAVDAT[ele][param])
            assert len(p) == 1
            return list(p)[0]

    L1phi0 = unique_param(LINAC["L1"], "PHI0")
    L2phi0 = unique_param(LINAC["L2"], "PHI0")
    L3phi0 = unique_param(LINAC["L3"], "PHI0")

    L1KLYS = list(set([c[:-1] for c in LINAC["L1"]]))

    # Get klystrons by linac
    L1KLYS = list(set([c[:-1] for c in LINAC["L1"]]))
    L2KLYS = sorted(list(set([c[:-1] for c in LINAC["L2"]])))
    L3KLYS = sorted(list(set([c[:-1] for c in LINAC["L3"]])))
    # Klystrons for L2, L3 feedback
    L2FEEDBACKKLYS = sorted(list(set([c[:-1] for c in L2FEEDBACK])))
    L3FEEDBACKKLYS = sorted(list(set([c[:-1] for c in L3FEEDBACK])))

    elegant["vars"]["O_L1_phase_deg"] = round(L1phi0 * 360, 9)
    elegant["vars"]["O_L2_phase_deg"] = round(L2phi0 * 360, 9)
    elegant["vars"]["O_L3_phase_deg"] = round(L3phi0 * 360, 9)

    for name in L2FEEDBACKKLYS:
        elegant["vars"][f"{name}_phase_deg"] = round(L2phi0 * 360, 9)

    for name in L3FEEDBACKKLYS:
        elegant["vars"][f"{name}_phase_deg"] = round(L3phi0 * 360, 9)

    # Make overlays
    def phase_overlay(name, cavs):
        for n in cavs:
            elegant["fields"][n]["phase"] += f" + {name}_phase_deg"

    # Make Subbooster overlays
    def sbst_overlay(sector, stations):
        name = f"SBST_{sector}"
        for station in stations:
            for ele in eles_in(sector, station):
                elegant["fields"][ele]["phase"] += f" + {name}_phase_deg"
        elegant["vars"][f"{name}_phase_deg"] = 0

    phase_overlay("O_L1", LINAC["L1"])
    phase_overlay("O_L2", L2FORPHASE)
    phase_overlay("O_L3", L3FORPHASE)

    SUBBOOSTER_STATIONS = {
        21: (3, 4, 5, 6, 7, 8),  # 21-1 (L1S) and 21-2 (L1X) dont use the subbooster.
        22: (1, 2, 3, 4, 5, 6, 7, 8),
        23: (1, 2, 3, 4, 5, 6, 7, 8),
        24: (
            4,
            5,
            6,
        ),  # 1,2,3 are feedback stations, no sbst.  7 is a tcav, 8 doesn't exist.
        25: (1, 2, 3, 4, 5, 6, 7, 8),
        26: (1, 2, 3, 4, 5, 6, 7, 8),
        27: (1, 2, 3, 4, 5, 6, 7, 8),
        28: (1, 2, 3, 4, 5, 6, 7, 8),
        29: (1, 2, 3, 4, 5, 6, 7, 8),
        30: (1, 2, 3, 4, 5, 6, 7, 8),
    }

    # Subbooster overlays
    for sector in SUBBOOSTER_STATIONS:
        sbst_overlay(sector, SUBBOOSTER_STATIONS[sector])
    elegant["klystrons"] = [
        name
        for name in NAMES
        if (name.startswith("K") or name == "L1X") and ("#" not in name)
    ]
