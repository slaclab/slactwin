#!/bin/bash
export 'PYKERN_PKCONFIG_CHANNEL=alpha'
export 'PYKERN_PKDEBUG_REDIRECT_LOGGING=1'
export 'PYKERN_PKDEBUG_WANT_PID_TIME=1'
export 'PYTHONUNBUFFERED=1'
export 'TZ=/etc/localtime'
export 'SLACTWIN_CONFIG_TCP_IP=0.0.0.0'
export 'SLACTWIN_CONFIG_TCP_PORT=9020'
export 'SLACTWIN_CONFIG_AUTH_SECRET=<SECRET>'
export 'SLACTWIN_DB_URI=postgresql://<USER>:<PASSWORD>@127.0.0.1/slactwin' # TODO(e-carlin): need to create a user and password
#not necessary until we have something live
#export 'SLACTWIN_RUN_IMPORTER_SUMMARY_DIR=' # TODO(e-carlin):  ???

# TODO(e-carlin):  auth secret
