"""Wraps SQLAlchemy

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkconfig
import pykern.sql_db
import pykern.util
import slactwin.config
import slactwin.quest
import sqlalchemy
import sqlalchemy.sql.operators
import sys


class _Db(slactwin.quest.Attr):
    """Database object bound to each `slactwin.quest`

    All quests automatically begin a transaction at start and commit
    on success or rollback on an exception.
    """

    ATTR_KEY = "db"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = _meta.session()

    def commit(self):
        self.commit_or_rollback(commit=True)

    def commit_or_rollback(self, commit):
        self.__session.commit_or_rollback(commit=commit)

    def query(self, name, **kwargs):
        return _queries[name](self.session, **kwargs)


def init_module():
    global _cfg, _meta, _queries
    from slactwin import db_query

    @pykern.pkconfig.parse_none
    def _uri(value):
        if value is None:
            return "sqlite:///" + str(
                slactwin.config.dev_path(slactwin.const.DEV_DB_BASENAME)
            )
        # create_engine will validate
        return value

    _cfg = pykern.pkconfig.init(
        uri=pykern.pkconfig.RequiredUnlessDev(
            None,  # "postgresql://vagrant@/slactwin",
            _uri,
            "sqlalchemy create_engine uri, e.g. postgresql://vagrant@/slactwin",
        ),
    )
    _meta = pykern.sql_db.Meta(
        uri=_cfg.uri,
        schema=PKDict(
            run_kind=PKDict(
                run_kind_id="primary_id 1",
                machine_name="str 64",
                twin_name="str 64",
                created="datetime",
                unique=(("machine_name", "twin_name"),),
            ),
            run_summary=PKDict(
                run_summary_id="primary_id 2",
                run_kind_id="primary_id",
                created="datetime index",
                run_end="datetime index",
                archive_path="str 1024 unique",
                snapshot_end="datetime index",
                snapshot_path="str 1024 unique",
                summary_path="str 1024 unique",
            ),
            run_value_name=PKDict(
                run_value_name_id="primary_id 3",
                created="datetime",
                run_kind_id="primary_id",
                name="str 64 index",
                unique=(("run_kind_id", "name"),),
            ),
            run_value_float=PKDict(
                run_summary_id="primary_id primary_key",
                run_value_name_id="primary_id primary_key",
                value="float 64 nullable",
                index=(("run_summary_id", "run_value_name_id", "value"),),
            ),
        ),
    )
    _queries = db_query.init_by_db(_meta)
    slactwin.quest.register_attr(_Db)
