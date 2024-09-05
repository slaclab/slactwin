#!/bin/bash
# Handle running as a user other than vagrant (1000)
export PYENV_ROOT=/home/vagrant/.pyenv
export HOME=/home/vagrant
source "$HOME"/.bashrc >& /dev/null
eval export HOME=~$USER

set -euo pipefail
cd '/srv/sirepo'
source ./env
cd /tmp
p=
for r in radiasoft/sirepo radiasoft/pykern slaclab/slactwin; do
    git clone -q -c advice.detachedHead=false --depth=1 https://github.com/"$r"
    p+="$PWD/${r#*/}:"
done
export PYTHONPATH=$p
# TODO(e-carlin): https://github.com/radiasoft/sirepo/issues/7238
echo '__version__ = "1.1" # TODO(e-carlin): https://github.com/radiasoft/sirepo/issues/7238' > slactwin/slactwin/__init__.py
cd -
if [[ $@ ]]; then
    exec "$@"
fi
exec sirepo service tornado
