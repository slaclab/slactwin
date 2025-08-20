"""Database queries

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
import inspect
import pykern.util
import re
import slactwin.const
import sqlalchemy

_query_builder = None


def init_by_db(meta):
    global _query_builder

    if _query_builder:
        raise AssertionError("duplicate initialization")
    _query_builder = _DbQueryBuilder(meta)
    return _query_builder.queries


class _DbQuery:
    def __init__(self, meta, name, method):
        self._name = name
        self._method = method
        self._tables = PKDict(self._init_tables(meta, method))

    def __call__(self, session, **kwargs):
        return self._method(self, session, **self._tables, **kwargs)

    def _init_tables(self, meta, method):
        for a in inspect.getfullargspec(method).args:
            if (t := meta.tables.get(a)) is not None:
                yield a, t

    def _query_max_run_summary(self, session, run_summary, run_kind, run_kind_id):
        return PKDict(
            session.select_one(
                sqlalchemy.select(run_summary).where(
                    run_summary.c.snapshot_end
                    == sqlalchemy.select(
                        sqlalchemy.func.max(run_summary.c.snapshot_end)
                    )
                    .where(
                        run_summary.c.run_kind_id == run_kind_id,
                    )
                    .scalar_subquery(),
                ),
            ),
        )

    def _query_run_kind_by_names(self, session, run_kind, machine_name, twin_name):
        return PKDict(
            session.select_one(
                sqlalchemy.select(run_kind).where(
                    run_kind.c.machine_name == machine_name,
                    run_kind.c.twin_name == twin_name,
                ),
            ),
        )

    def _query_run_kinds_and_values(self, session, run_kind, run_value_name):

        def _add(rv, machine_name, twin_name, run_value_name):
            x = _add_level(rv, "machines", machine_name)
            x = _add_level(x, "twins", twin_name)
            x.pksetdefault("run_values", list).run_values.append(run_value_name)

        def _add_level(pkdict, kind, name):
            if kind not in pkdict:
                pkdict[kind] = PKDict({name: PKDict()})
            elif name not in pkdict[kind]:
                pkdict[kind][name] = PKDict()
            return pkdict[kind][name]

        rv = PKDict()
        for r in session.select(
            sqlalchemy.select(
                [run_kind.c.machine_name, run_kind.c.twin_name, run_value_name.c.name]
            )
            .join(
                run_value_name,
                run_kind.c.run_kind_id == run_value_name.c.run_kind_id,
            )
            .order_by(
                run_kind.c.machine_name, run_kind.c.twin_name, run_value_name.c.name
            )
        ):
            _add(rv, r[0], r[1], r[2])
        return rv

    def _query_run_summary_by_id(self, session, run_summary, run_summary_id):
        return PKDict(
            session.select_one(
                sqlalchemy.select(run_summary).where(
                    run_summary.c.run_summary_id == run_summary_id,
                )
            )
        )

    def _query_run_summary_path_exists(self, session, run_summary, summary_path):
        return (
            session.select_one_or_none(
                sqlalchemy.select(run_summary).where(
                    run_summary.c.summary_path == summary_path,
                )
            )
            is not None
        )

    def _query_run_value(
        self, session, run_value_name, run_value_float, run_summary_id, tag, base
    ):
        return session.select_one(
            sqlalchemy.select(run_value_float)
            .join(
                run_value_name,
                run_value_float.c.run_value_name_id
                == run_value_name.c.run_value_name_id,
            )
            .where(
                run_value_name.c.name == tag + slactwin.const.RUN_VALUE_SEP + base,
                run_value_float.c.run_summary_id == run_summary_id,
            )
        ).value

    def _query_runs_by_date_and_values(
        self,
        session,
        run_kind,
        run_summary,
        run_value_name,
        run_value_float,
        machine_name,
        twin_name,
        min_max_values,
        additional_run_values,
    ):
        def _additional(state):
            v = PKDict()
            for n in additional_run_values:
                _add_value(state, n, v)
            return state

        def _add_date_time(state, name, col, values):
            if values:
                _add_min_max(state, col, values)
            state.base_cols[name] = col
            state.order_by.append(col.desc())

        def _add_min_max(state, col, values):
            if (x := values.get("min")) is not None:
                state.where.append(col >= x)
            if (x := values.get("max")) is not None:
                state.where.append(col <= x)

        def _add_value(state, name, values):
            n = run_value_name.alias(f"rn{state.index}")
            v = run_value_float.alias(f"rv{state.index}")
            state.index += 1
            state.value_cols[n.name] = n.c.name
            state.value_cols[v.name] = v.c.value
            state.select_from = state.select_from.join(
                n, run_summary.c.run_kind_id == n.c.run_kind_id
            ).join(v, run_summary.c.run_summary_id == v.c.run_summary_id)
            state.where.extend(
                [
                    n.c.name == name,
                    n.c.run_value_name_id == v.c.run_value_name_id,
                ]
            )
            _add_min_max(state, v.c.value, values)

        def _min_max_values(state):
            _add_date_time(
                state,
                "snapshot_end",
                run_summary.c.snapshot_end,
                min_max_values.pkdel("snapshot_end"),
            )
            for k, v in min_max_values.items():
                # TODO(robnagler) assert criteria values
                if slactwin.const.RUN_VALUE_SEP in k:
                    _add_value(state, k, v)
                else:
                    raise pykern.util.APIError(
                        "invalid runs_by_date_and_values min_max_values name={}", k
                    )
            return state

        def _rows(state, select):

            def _row(row):
                r = list(row)
                for c in state.base_cols.keys():
                    yield c, r.pop(0)
                yield "run_values", PKDict(_run_values(r))

            def _run_values(row):
                while row:
                    yield row.pop(0), row.pop(0)

            return PKDict(rows=[PKDict(_row(r)) for r in select])

        def _select(state):
            return session.select(
                sqlalchemy.select(
                    tuple(state.base_cols.values()) + tuple(state.value_cols.values())
                )
                .select_from(state.select_from)
                .where(*state.where)
                .order_by(*state.order_by),
            )

        def _state():
            return PKDict(
                index=1,
                base_cols=PKDict(
                    run_summary_id=run_summary.c.run_summary_id,
                    snapshot_path=run_summary.c.snapshot_path,
                    archive_path=run_summary.c.archive_path,
                    summary_path=run_summary.c.summary_path,
                ),
                value_cols=PKDict(),
                select_from=run_summary,
                where=[],
                order_by=[],
            )

        s = _state()
        return _rows(s, _select(_additional(_min_max_values(s))))


class _DbQueryBuilder:
    def __init__(self, meta):
        self.queries = PKDict(self._init_queries(meta))

    def _init_queries(self, meta):
        for k, v in inspect.getmembers(_DbQuery, predicate=inspect.isfunction):
            if m := re.search(r"^_query_(\w+)$", k):
                yield (m.group(1), _DbQuery(meta, m.group(1), v))
