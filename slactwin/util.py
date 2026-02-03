"""Common utilities

:copyright: Copyright (c) 2026 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
import h5py
import pandas


def summary_from_archive(archive_path):
    s = PKDict(outputs=PKDict())
    with h5py.File(archive_path, "r") as f:
        g = f["summary"]
        for n in ("isotime", "machine_name", "twin_name"):
            s[n] = g.attrs[n]
        o = g["outputs"]
        for n in o.attrs:
            s.outputs[n] = o.attrs[n]
        has_pv_dataframe = "pv_mapping_dataframe" in g
    if has_pv_dataframe:
        s.pv_mapping_dataframe = pandas.read_hdf(
            archive_path, key="/summary/pv_mapping_dataframe"
        )
    else:
        s.pv_mapping_dataframe = pandas.DataFrame([])
    return s
