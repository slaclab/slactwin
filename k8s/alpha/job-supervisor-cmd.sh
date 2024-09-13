#!/bin/bash
source /srv/slactwin_db/python-init.sh
set -euo pipefail
cd /srv/sirepo_job_supervisor
source ./env
if [[ $@ ]]; then
    exec "$@"
fi
exec sirepo job_supervisor
