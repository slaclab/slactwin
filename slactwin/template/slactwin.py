"""Execution template.

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo.template.impactt_parser import ImpactTParser
import asyncio
import h5py
import impact
import pykern.pkio
import pykern.pkjson
import sirepo.sim_data
import sirepo.template.impactt
import sirepo.template.lattice
import sirepo.util
import slactwin.db_api_client


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


class DummyDB:
    _DB = [
        PKDict(
            archiveId=589,
            archiveType="sc_inj",
            description="sc_inj 2024-06-19T06:03:38",
            summaryFile="lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:03:38-07:00.json",
        ),
        PKDict(
            archiveId=612,
            archiveType="sc_inj",
            description="sc_inj 2024-06-19T06:23:47",
            summaryFile="lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:23:47-07:00.json",
        ),
    ]

    def get_archive(self, archive_id):
        return [v for v in self._DB if v.archiveId == archive_id][0]

    def get_next_and_previous_archives(self, archive_id):
        # Returns a [prev id, next id] pair for the current archive_id
        # Should only return ids for the same type of archive (sc_inj, lcls, facet, etc)
        res = None
        prev = None
        for v in self._DB:
            if res:
                res[1] = v.archiveId
                break
            if v.archiveId == archive_id:
                res = [prev, None]
                continue
            prev = v.archiveId
        return res

    def search_archives(self, *kwargs):
        return self._DB


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            frameCount=0,
            percentComplete=0,
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
    )


def sim_frame(frame_args):
    return sirepo.template.impactt.bunch_plot(
        frame_args,
        frame_args.frameIndex,
        _load_archive(frame_args).output["particles"][frame_args.plotName],
    )


def sim_frame_statAnimation(frame_args):
    return sirepo.template.impactt.stat_animation(_load_archive(frame_args), frame_args)


def sim_frame_summaryAnimation(frame_args):
    s = _summary_file(frame_args.archiveId)
    I = _load_archive(frame_args)
    # l = ImpactTParser().parse_file(I['input']['original_input'])
    # l.models.simulation.visualizationBeamlineId = l.models.beamlines[0].id
    with h5py.File(s.outputs.archive) as f:
        l = ImpactTParser().parse_file(f["/impact/input"].attrs["ImpactT.in"])
        l.models.simulation.visualizationBeamlineId = l.models.beamlines[0].id
    return PKDict(
        summary=PKDict(
            pv_mapping_dataframe=s.pv_mapping_dataframe,
            inputs=s.inputs,
            outputs=s.outputs,
            run_time=I.output["run_info"]["run_time"],
            Nbunch=I.header["Nbunch"],
            Nprow=I.header["Nprow"],
            Npcol=I.header["Npcol"],
            description=DummyDB().get_archive(frame_args.archiveId).description,
        ),
        lattice=_trim_beamline(l),
        particles=sirepo.template.impactt.output_info(l),
    )


def stateless_compute_db_api(data, **kwargs):
    return asyncio.run(
        slactwin.db_api_client.DbAPIClient().post(
            data.args.api_name, data.args.api_args
        )
    )


def stateful_compute_next_and_previous_archives(data, **kwards):
    return PKDict(
        archiveIds=DummyDB().get_next_and_previous_archives(int(data.args.archiveId)),
    )


def stateful_compute_search_archives(data, **kwargs):
    return PKDict(
        searchResults=DummyDB().search_archives(),
    )


def write_parameters(data, run_dir, is_parallel):
    pass


def _load_archive(frame_args):
    return impact.Impact.from_archive(
        _summary_file(frame_args.archiveId).outputs.archive
    )


def _summary_file(archive_id):
    return pykern.pkjson.load_any(
        pykern.pkio.py_path(_cfg.summary_dir).join(
            DummyDB().get_archive(archive_id).summaryFile
        ),
    )


def _trim_beamline(data):
    # remove zero quads and trim beamline at STOP element
    util = sirepo.template.lattice.LatticeUtil(
        data, sirepo.sim_data.get_class("impactt").schema()
    )
    bl = []
    for i in data.models.beamlines[0]["items"]:
        el = util.id_map[i]
        if el.get("type") == "QUADRUPOLE":
            if el.rf_frequency == 0:
                continue
        bl.append(i)
        if el.get("type") == "STOP":
            break
    data.models.beamlines[0]["items"] = bl
    return data


_cfg = pkconfig.init(
    summary_dir=(
        "/home/vagrant/save/slactwin/sirepo-test/summary/",
        str,
        "Location of lume-live json summary files",
    ),
)
