#!/bin/bash

# adjust paths below
# see https://docs.kustosz.org/en/stable/installation/vps.html
export KUSTOSZ_BASE_DIR="$HOME/kustosz_home"
export VIRTUAL_ENV="$HOME/.virtualenvs/kustosz"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export ENV_FOR_DYNACONF="production"
export DJANGO_SETTINGS_MODULE=kustosz.settings

kustosz-manager fetch_new_content --wait
