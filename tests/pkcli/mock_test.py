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

    def _touch(path):
        p = pkio.py_path(path)
        pkio.mkdir_parent_only(p)
        p.ensure(file=True)

    _ARCHIVE_PATH_RE = re.compile(
        r"(.*)/summary/(\d{4}/\d\d/\d\d/).+-(\w+)-\d{4}-\d\d-\d\dT"
    )
    with pkio.save_chdir(pkunit.work_dir().join("live"), mkdir=True) as d:
        subprocess.run(
            ["tar", "xzf", str(pkunit.data_dir().join("iana.tgz"))],
        )
        rv = []
        for p in pkio.walk_tree(".", file_re=r"\.h5$"):
            _touch(p)
            rv.append(p)
        pkconfig.reset_state_for_testing(
            PKDict(
                SLACTWIN_RUN_IMPORTER_ARCHIVE_DIR=str(
                    rv[0].dirpath().dirpath().dirpath()
                )
            )
        )
        return rv
