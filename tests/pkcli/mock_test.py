"""Test mock_live

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""


def test_live():
    from pykern.pkcollections import PKDict
    from pykern import pkunit, pkio, pkdebug

    def _check(summaries):
        pkdebug.pkdlog("{}", summaries)
        for i, s in enumerate(summaries):
            if i == 0:
                pkunit.pkok(
                    summaries[0].exists(), "missing summary[0] summaries={}", summaries
                )
            else:
                pkunit.pkok(
                    not summaries[i].exists(),
                    "exists summary[{}] summaries={}",
                    i,
                    summaries,
                )
        summaries.pop(0)

    s = _setup()
    from slactwin.pkcli import mock

    mock.time = PKDict(sleep=lambda x: _check(s))
    mock.Commands().live()
    # Last call to time.sleep doesn't happen
    pkunit.pkeq(1, len(s))


def _setup():
    import subprocess, re
    from pykern.pkcollections import PKDict
    from pykern import pkunit, pkio, pkdebug, pkjson, pkconfig

    def _fixup_one(json_d, kind, base):
        return re.sub("/summary/", f"/{kind}/", str(json_d.join(base)))

    def _fixup_paths(json_d, parsed, root, prefix):
        o = parsed.outputs
        o.archive = _fixup_one(json_d, "archive", pkio.py_path(o.archive).basename)
        o.plot_file = _fixup_one(json_d, "plot", pkio.py_path(o.plot_file).basename)
        return _fixup_one(json_d, "snapshot", f"sc_inj-snapshot-{parsed.isotime}.h5")

    def _touch(path):
        p = pkio.py_path(path)
        pkio.mkdir_parent_only(p)
        p.ensure(file=True)

    _SUMMARY_PATH_RE = re.compile(
        r"(.*)/summary/(\d{4}/\d\d/\d\d/).+-(\w+)-\d{4}-\d\d-\d\dT"
    )
    with pkio.save_chdir(pkunit.work_dir().join("live"), mkdir=True) as d:
        subprocess.run(
            ["tar", "xzf", str(pkunit.data_dir().join("iana.tgz"))],
        )
        rv = []
        for p in pkio.walk_tree(".", file_re=r"\.json$"):
            # change absolute paths
            m = _SUMMARY_PATH_RE.search(str(p))
            d = pkjson.load_any(p)
            _touch(_fixup_paths(p.dirpath(), d, m.group(1), m.group(2)))
            _touch(d.outputs.archive)
            pkjson.dump_pretty(d, filename=p)
            rv.append(p)
        pkconfig.reset_state_for_testing(
            PKDict(
                SLACTWIN_RUN_IMPORTER_SUMMARY_DIR=str(
                    rv[0].dirpath().dirpath().dirpath()
                )
            )
        )
        return rv
