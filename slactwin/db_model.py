"""Database models and querys

api
   return list of all run kinds and run value names and run_date
api
   run_date min max
   search start_dt and stop_dt
   search run value names with min and max
   list of return value names
   summary_path
   achirve_path
   return cols with order by date time


:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkio
import datetime
import inspect
import os.path
import sqlalchemy

PATH = sqlalchemy.types.String(1024)
PRIMARY_ID = sqlalchemy.types.BigInteger()
PRIMARY_ID_INC = 1000
RUN_VALUE_NAME = sqlalchemy.types.String(1024)
# precision is mantissa bits so force to double (doesn't work with all dbs)
RUN_VALUE_FLOAT = sqlalchemy.types.Float(precision=53)
RUN_KIND_NAME = sqlalchemy.types.String(64)
DATE_TIME = sqlalchemy.types.DateTime()

_model_builder = None


def init_by_db(engine):
    global _model_builder

    if _model_builder:
        raise AssertionError("duplicate initialization")
    _model_builder = _DbModelBuilder(engine)
    return _model_builder.models


class _DbModelBuilder:
    def __init__(self, engine):
        self.metadata = sqlalchemy.MetaData()
        self.models = PKDict()
        self._table_to_models = PKDict()
        self._primary_id_cols = PKDict()
        self._init_models()
        self.metadata.create_all(bind=engine)

    def _init_models(self):
        def _col(name, stype, **kwargs):
            return PKDict(name=name, stype=stype, **kwargs)

        self._model(
            "RunKind",
            "run_kind_t",
            _col("run_kind_id", PRIMARY_ID, sequence=1),
            _col("machine_name", RUN_KIND_NAME),
            _col("twin_name", RUN_KIND_NAME),
            _col("created", DATE_TIME),
            unique=(("machine_name", "twin_name"),),
        )
        self._model(
            "RunSummary",
            "run_summary_t",
            _col("run_summary_id", PRIMARY_ID, sequence=2),
            _col("run_kind_id", PRIMARY_ID),
            _col("created", DATE_TIME, index=True),
            _col("run_end", DATE_TIME, index=True),
            _col("archive_path", PATH, unique=True),
            _col("snapshot_end", DATE_TIME, index=True),
            _col("snapshot_path", PATH, unique=True),
            _col("summary_path", PATH, unique=True),
        )
        self._model(
            "RunValueName",
            "run_value_name_t",
            _col("run_value_name_id", PRIMARY_ID, sequence=3),
            _col("created", DATE_TIME),
            _col("run_kind_id", PRIMARY_ID),
            _col("name", RUN_VALUE_NAME, index=True),
            unique=(("run_kind_id", "name"),),
        )
        self._model(
            "RunValueFloat",
            "run_value_float_t",
            _col("run_summary_id", PRIMARY_ID, primary_key=True),
            _col("run_value_name_id", PRIMARY_ID, primary_key=True),
            _col("value", RUN_VALUE_FLOAT, nullable=True),
            index=(("run_summary_id", "run_value_name_id", "value"),),
        )

    def _model(self, model_name, table_name, *args, **kwargs):
        self._table_to_models[table_name] = self.models[model_name] = _DbModel(
            model_name,
            self._table(table_name, *args, **kwargs),
        )

    def _table(self, table_name, *cols, index=(), unique=()):
        def _args():
            rv = [table_name, self.metadata]
            for x in cols:
                rv.append(_column(x))
            for x in index:
                rv.append(sqlalchemy.Index(*x))
            for x in unique:
                rv.append(sqlalchemy.UniqueConstraint(*x))
            return rv

        def _column(decl):
            a = [decl.name, decl.stype]
            if decl.stype is PRIMARY_ID:
                _column_primary_id(decl, a)
            if decl.get("unique"):
                decl.index = True
            decl.pksetdefault(nullable=False)
            decl.pkdel("name")
            decl.pkdel("stype")
            return sqlalchemy.Column(*a, **decl)

        def _column_primary_id(decl, args):
            if s := decl.pkdel("sequence"):
                args.append(
                    sqlalchemy.Sequence(
                        f"{decl.name}_seq",
                        start=PRIMARY_ID_INC + s,
                        increment=PRIMARY_ID_INC,
                    )
                )
                if decl.name in self._primary_id_cols:
                    raise AssertionError(
                        f"duplicate column={decl.name} table={table_name}"
                    )
                self._primary_id_cols[decl.name] = table_name
                decl.primary_key = True
            elif n := self._primary_id_cols.get(decl.name):
                args.append(sqlalchemy.ForeignKey(f"{n}.{decl.name}"))
                decl.index = True
            else:
                # TODO more flexible some day
                raise AssertionError(f"invalid primary_id decl={decl}")

        return sqlalchemy.Table(*_args())


class _DbModel:
    def __init__(self, name, table):
        self.table = table
        self.name = name
        self.has_created = "created" in table.columns
        # primary_id only needed for sqlite (see db.insert)
        c = list(table.primary_key)[0]
        self.has_primary_id = isinstance(c.default, sqlalchemy.Sequence)
        if self.has_primary_id:
            self.primary_id = c.name
            self.primary_id_start = c.default.start

    def fixup_insert(self, db, values):
        rv = None
        if self.has_created and "created" not in values:
            values["created"] = datetime.datetime.utcnow()
        if db.is_sqlite and self.has_primary_id and self.primary_id not in values:
            v = db.select_max_primary_id(self.name)
            values[self.primary_id] = (
                self.primary_id_start if v is None else v + PRIMARY_ID_INC
            )
            # mock the RETURNING result like Postgres does
            rv = PKDict({self.primary_id: values[self.primary_id]})
        return rv
