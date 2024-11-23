"""
Django settings are managed by dynaconf - see settings.yaml in parent directory
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
PROJECT_DIR = Path(__file__).resolve().parent.parent

BASE_DIR = PROJECT_DIR
try:
    BASE_DIR = Path(os.environ["KUSTOSZ_BASE_DIR"])
except KeyError:
    pass

import dynaconf  # noqa

settings = dynaconf.DjangoDynaconf(
    __name__,
    settings_files=[
        BASE_DIR / "settings/settings.yaml",
        BASE_DIR / "settings/.secrets.yaml",
    ],
)  # noqa
