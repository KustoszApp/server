#!/usr/bin/env bash
#
# https://github.com/olivergondza/bash-strict-mode
set -euo pipefail
trap 's=$?; echo >&2 "$0: Error on line "$LINENO": $BASH_COMMAND"; exit $s' ERR

# ensure we have db connection
DJANGODB=$(mktemp --suffix=.json)
dynaconf list -k DATABASES__default --output-flat -o "$DJANGODB" > /dev/null

if ! jq '.DATABASES__default.ENGINE' "$DJANGODB" |grep -q sqlite3 ; then
    DB_HOST="$(jq '.DATABASES__default.HOST' "$DJANGODB")"
    DB_PORT="$(jq '.DATABASES__default.PORT' "$DJANGODB")"
    echo "Waiting for db"
    while ! nc -z "$DB_HOST" "$DB_PORT"; do
        sleep 0.1
    done
    echo "db started"
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

if [ -z "${@:+x}" ]; then
    exec gunicorn kustosz.wsgi --bind 0.0.0.0:8000
fi

exec "$@"
