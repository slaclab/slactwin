#!/bin/bash
source /srv/slactwin_db/python-init.sh
set -eou pipefail
source /srv/slactwin_db/env
slactwin db insert_runs /srv/slactwin_db/lume-impact-live/summary
