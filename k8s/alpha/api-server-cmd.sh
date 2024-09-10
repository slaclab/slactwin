#!/bin/bash
source /srv/slactwin_db/python-init.sh
set -euo pipefail
cd /srv/sirepo
source ./env
if [[ $@ ]]; then
    exec "$@"
fi
exec sirepo service tornado
