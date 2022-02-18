#!/usr/bin/env bash
#
# https://github.com/olivergondza/bash-strict-mode
set -euo pipefail
trap 's=$?; echo >&2 "$0: Error on line "$LINENO": $BASH_COMMAND"; exit $s' ERR

if [ -z "${KUSTOSZ_DONT_WAIT_FOR_POSTGRES:+x}" ]; then
    echo "Waiting for postgres..."

    # FIXME: czy mogę mieć te same zmienne co w dynaconf?
    while ! nc -z $SQL_HOST $SQL_PORT; do
        sleep 0.1
    done

    echo "PostgreSQL started"
fi

if [ -z "${KUSTOSZ_SKIP_MIGRATE:+x}" ]; then
    kustosz-manager migrate --noinput
fi

if [ -z "${KUSTOSZ_SKIP_COLLECTSTATIC:+x}" ]; then
    kustosz-manager collectstatic
fi

exec "$@"
