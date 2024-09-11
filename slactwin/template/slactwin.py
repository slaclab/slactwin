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

# TODO(pjm): remove this when template.slactwin can query the database
_ALL_RECORDS = PKDict(
    {
        1002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T00:01:29-07:00.json",
        2002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:08:47-07:00.json",
        3002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:11:28-07:00.json",
        4002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:13:40-07:00.json",
        5002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:16:29-07:00.json",
        6002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:19:13-07:00.json",
        7002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:22:32-07:00.json",
        8002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:25:10-07:00.json",
        9002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:27:53-07:00.json",
        10002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:30:39-07:00.json",
        11002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:33:13-07:00.json",
        12002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:35:54-07:00.json",
        13002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:38:34-07:00.json",
        14002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:45:07-07:00.json",
        15002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T03:48:12-07:00.json",
        16002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T04:56:49-07:00.json",
        17002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T04:59:39-07:00.json",
        18002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T05:16:38-07:00.json",
        19002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T05:19:20-07:00.json",
        20002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T05:23:18-07:00.json",
        21002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T05:36:25-07:00.json",
        22002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T05:40:58-07:00.json",
        23002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T05:45:08-07:00.json",
        24002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T05:49:17-07:00.json",
        25002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T05:53:47-07:00.json",
        26002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T05:58:58-07:00.json",
        27002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:03:38-07:00.json",
        28002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:08:38-07:00.json",
        29002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:13:39-07:00.json",
        30002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:18:04-07:00.json",
        31002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:23:47-07:00.json",
        32002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:28:20-07:00.json",
        33002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:32:33-07:00.json",
        34002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:37:36-07:00.json",
        35002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:42:21-07:00.json",
        36002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:47:38-07:00.json",
        37002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:53:18-07:00.json",
        38002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T06:58:07-07:00.json",
        39002: "/home/vagrant/save/slactwin/iana-data/iana/summary/2024/06/19/lume-impact-live-demo-s3df-sc_inj-2024-06-19T07:03:29-07:00.json",
    }
)


class DummyDB:
    def get_archive(self, archive_id):
        p = _ALL_RECORDS[int(archive_id)]
        assert p
        return PKDict(
            archiveId=archive_id,
            archiveType="sc_inj",
            description="",
            summaryFile=p,
        )


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
            # TODO(pjm): need summary of archive: date/time, machine, model
            description="",
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


def write_parameters(data, run_dir, is_parallel):
    pass


def _load_archive(frame_args):
    return impact.Impact.from_archive(
        _summary_file(frame_args.archiveId).outputs.archive
    )


def _summary_file(archive_id):
    s = DummyDB().get_archive(archive_id).summaryFile
    return pykern.pkjson.load_any(pykern.pkio.py_path(s))


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
