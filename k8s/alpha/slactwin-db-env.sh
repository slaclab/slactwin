#!/bin/bash
export 'PYKERN_PKCONFIG_CHANNEL=alpha'
export 'PYKERN_PKDEBUG_REDIRECT_LOGGING=1'
export 'PYKERN_PKDEBUG_WANT_PID_TIME=1'
export 'PYTHONUNBUFFERED=1'
export 'TZ=/etc/localtime'
export 'SLACTWIN_CONFIG_TCP_IP=0.0.0.0'
export 'SLACTWIN_CONFIG_TCP_PORT=9020'
export 'SLACTWIN_DB_URL=xxx' # TODO(e-carlin):  ???
export 'SLACTWIN_RUN_IMPORTER_SUMMARY_DIR=' # TODO(e-carlin):  ???

# TODO(e-carlin):  auth secret
