#!/bin/bash
# No set -e because pyenv rehash causes error even though it can be ignored
python_init_main() {
    export PYENV_ROOT=/home/vagrant/.pyenv
    export HOME=/home/vagrant
    source "$HOME"/.bashrc >& /dev/null
    eval export HOME=~$USER
    source /srv/slactwin_db/env
    mkdir -p /tmp/user-home
    cd $_
    mkdir bin
    mkdir python
    export PYTHONPATH=$PWD/python/
    mkdir src
    cd src
    for r in radiasoft/pykern radiasoft/sirepo slaclab/slactwin; do
        git clone -q -c advice.detachedHead=false --depth=1 https://github.com/"$r"
        cd "${r#*/}"
        pip install --target=$PYTHONPATH .
        cd ..
    done
    pip install --target=$PYTHONPATH psycopg2-binary
    install -m 700 /dev/stdin /tmp/user-home/bin/slactwin<<'EOF'
#!/usr/bin/env python
EOF
    cat /tmp/user-home/src/slactwin/slactwin/slactwin_console.py >> /tmp/user-home/bin/slactwin
    export PATH=/tmp/user-home/bin/:$PATH
}

python_init_main
