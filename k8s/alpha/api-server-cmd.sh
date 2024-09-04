#!/bin/bash
# Handle running as a user other than vagrant (1000)
export PYENV_ROOT=/home/vagrant/.pyenv
export HOME=/home/vagrant
source "$HOME"/.bashrc >& /dev/null
eval export HOME=~$USER

set -euo pipefail
cd '/srv/sirepo'
source ./env
if [[ $@ ]]; then
    exec "$@"
fi
exec sirepo service tornado
