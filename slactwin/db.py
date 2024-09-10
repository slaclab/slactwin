"""Database connections

  su -
  dnf install -y postgresql-server postgresql-devel
  postgresql-setup --initdb
  systemctl start postgresql
  systemctl enable postgresql
  su postgres -c 'createuser --no-superuser --createdb --no-createrole --no-password vagrant'
  exit
  pip install psycopg2
  createdb slactwin
  SLACTWIN_DB_URL=postgresql://vagrant@/slactwin pykern test run_importer_test.py

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkconfig
import pykern.util
import slactwin.config
import slactwin.quest
import sqlalchemy
import sqlalchemy.sql.operators
import sys


class _Db(slactwin.quest.Attr):

    ATTR_KEY = "db"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conn = None
        self._txn = None
        self.is_sqlite = _cfg.url.startswith("sqlite")

    def column_map(self, model, key_col, value_col, **where):
        return PKDict({r[key_col]: r[value_col] for r in self.select(model, **where)})

    def commit(self):
        self.commit_or_rollback(commit=True)

    def commit_or_rollback(self, commit):
        if self._conn is None:
            return
        c = self._conn
        t = self._txn
        try:
            self._conn = None
            self._txn = None
            if commit:
                t.commit()
            else:
                t.rollback()
        finally:
            c.close()

    def destroy(self, commit=False, **kwargs):
        self.commit_or_rollback(commit=commit)

    def execute(self, stmt):
        return self.__conn().execute(stmt)

    def insert(self, model, **values):
        m = _models[model]
        rv = m.fixup_insert(self, values)
        r = self.execute(m.table.insert().values(**values))
        if rv := getattr(r, "inserted_primary_key"):
            return rv
        return rv

    def query(self, name, **kwargs):
        return _queries[name](self, **kwargs)

    def rollback(self):
        self.commit_or_rollback(commit=False)

    def select(self, model_or_stmt, **where):
        def _stmt(table):
            rv = sqlalchemy.select(table)
            if where:
                rv.where(
                    *(
                        sqlalchemy.sql.operators.eq(table.columns[k], v)
                        for k, v in where.items()
                    )
                )
            return rv

        return self.execute(
            _stmt(_models[model_or_stmt].table)
            if isinstance(model_or_stmt, str)
            else model_or_stmt
        )

    def select_max_primary_id(self, model):
        m = _models[model]
        return self.execute(
            sqlalchemy.select(
                sqlalchemy.func.max(m.table.columns[m.primary_id]),
            )
        ).scalar()

    def select_or_insert(self, model, **values):
        if m := self.select_one_or_none(model, **values):
            return m
        return self.insert(model, **values)

    def select_one(self, model_or_stmt, **where):
        if rv := self.select_one_or_none(model_or_stmt, **where):
            return rv
        raise ValueError(
            f"no value returned model_or_stmt={model_or_stmt} where={where}"
        )

    def select_one_or_none(self, model_or_stmt, **where):
        rv = None
        for x in self.select(model_or_stmt, **where):
            if rv is not None:
                raise ValueError(
                    f"more than one returned model_or_stmt={model_or_stmt} where={where}"
                )
            rv = x
        return rv

    def __conn(self):
        if self._conn is None:
            self._conn = _engine.connect()
            self._txn = self._conn.begin()
        return self._conn


def init_module():
    global _cfg, _engine, _is_sqlite, _models, _queries
    from slactwin import db_model, db_query

    @pykern.pkconfig.parse_none
    def _path(value):
        if value is not None:
            return pykern.util.cfg_absolute_dir(value)
        return slactwin.config.dev_path("summary").ensure(dir=True, ensure=True)

    @pykern.pkconfig.parse_none
    def _url(value):
        if value is None:
            return "sqlite:///" + str(
                slactwin.config.dev_path(slactwin.const.DEV_DB_BASENAME)
            )
        # create_engine will validate
        return value

    _cfg = pykern.pkconfig.init(
        debug=(False, bool, "turn on sqlalchemy tracing"),
        url=pykern.pkconfig.RequiredUnlessDev(
            None,  # "postgresql://vagrant@/slactwin",
            _url,
            "sqlalchemy create_engine URL, e.g. postgresql://vagrant@/slactwin",
        ),
    )
    # TODO(robnagler): need to set connection args, e.g. pooling
    _engine = sqlalchemy.create_engine(_cfg.url, echo=_cfg.debug)
    _models = slactwin.db_model.init_by_db(_engine)
    _queries = slactwin.db_query.init_by_db(_models)
    slactwin.quest.register_attr(_Db)