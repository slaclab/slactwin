# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        cls._init_models(data.models)

    @classmethod
    def _compute_job_fields(cls, data, *args, **kwargs):
        return [
            data.report,
        ]

    @classmethod
    def _lib_file_basenames(cls, *args, **kwargs):
        return []
