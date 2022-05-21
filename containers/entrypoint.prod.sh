#!/usr/bin/env bash
#
# https://github.com/olivergondza/bash-strict-mode
set -euo pipefail
trap 's=$?; echo >&2 "$0: Error on line "$LINENO": $BASH_COMMAND"; exit $s' ERR
shopt -s nullglob

# load Node.JS provided by nvm
[ -s "$NVM_DIR/nvm.sh"  ] && source "$NVM_DIR/nvm.sh"

# ensure we have db connection
DJANGODB=$(mktemp --suffix=.json)
dynaconf list -k DATABASES__default --output-flat -o "$DJANGODB" > /dev/null

if ! jq '.DATABASES__default.ENGINE' "$DJANGODB" |grep -q sqlite3 ; then
    DB_HOST="$(jq -r '.DATABASES__default.HOST' "$DJANGODB")"
    DB_PORT="$(jq -r '.DATABASES__default.PORT' "$DJANGODB")"
    wait-for-it "$DB_HOST":"$DB_PORT" -t 120
    unset DB_HOST
    unset DB_PORT
fi
rm "$DJANGODB"

# run migrate by default
if [ -z "${KUSTOSZ_SKIP_MIGRATE:+x}" ]; then
    kustosz-manager migrate --noinput
fi

# create cache table by default
if [ -z "${KUSTOSZ_SKIP_CREATECACHETABLE:+x}" ]; then
    kustosz-manager createcachetable
fi

# run collectstatic by default
if [ -z "${KUSTOSZ_SKIP_COLLECTSTATIC:+x}" ]; then
    kustosz-manager collectstatic --noinput
fi

# run celery and redis by default
if [ -z "${KUSTOSZ_ORCHESTRATED:+x}" ]; then
    supervisord -c $HOME/supervisor/supervisord.conf
    supervisorctl -c $HOME/supervisor/supervisord.conf start redis-server
fi

# set username and password by default, unless provided explicitly
if [ -z "${KUSTOSZ_SKIP_PASSWORD_GENERATION:+x}" ] && [ -z "${KUSTOSZ_USERNAME:+x}" ] && [ -z "${KUSTOSZ_PASSWORD:+x}" ]; then
    export KUSTOSZ_USERNAME="admin"
    export KUSTOSZ_PASSWORD="$(openssl rand -base64 30)"
    export KUSTOSZ_PASSWORD_GENERATED=1
fi

# maybe create user, if variables are provided / generated
if [ ! -z "${KUSTOSZ_USERNAME:+x}" ] && [ ! -z "${KUSTOSZ_PASSWORD:+x}" ]; then
    if ! (
        echo "from django.contrib.auth import get_user_model"
        echo "get_user_model().objects.get(username='${KUSTOSZ_USERNAME}')"
    ) | kustosz-manager shell >/dev/null 2>&1 ; then
        kustosz-manager createsuperuser --no-input --username "$KUSTOSZ_USERNAME" --email user${RANDOM}@example.invalid
        (
            echo "from django.contrib.auth import get_user_model"
            echo "user = get_user_model().objects.get(username='${KUSTOSZ_USERNAME}')"
            echo "user.set_password('${KUSTOSZ_PASSWORD}')"
            echo "user.save(update_fields=('password',))"
        ) | kustosz-manager shell

        if [ ! -z "${KUSTOSZ_PASSWORD_GENERATED:+x}" ]; then
            echo "Generated random login credentials"
            echo "Username: ${KUSTOSZ_USERNAME}"
            echo "Password: ${KUSTOSZ_PASSWORD}"
            echo ""
        fi
    fi
fi

# import channels from opml, if variable is provided
if [ ! -z "${KUSTOSZ_IMPORT_CHANNELS_DIR:+x}" ]; then
    for OPMLFILE in "$KUSTOSZ_IMPORT_CHANNELS_DIR"/* ; do
        kustosz-manager import_channels --file "$OPMLFILE" opml
    done
fi

if [ -z "${@:+x}" ]; then
    exec gunicorn kustosz.wsgi --bind 0.0.0.0:8000
fi

exec "$@"
