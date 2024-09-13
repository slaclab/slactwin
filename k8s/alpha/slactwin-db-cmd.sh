#!/bin/bash
source /srv/slactwin_db/python-init.sh
set -euo pipefail
cd /srv/slactwin_db
source ./env
if [[ $@ ]]; then
    exec "$@"
fi
exec slactwin service db
