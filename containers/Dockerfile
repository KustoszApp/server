# vim: fdm=marker
# NOTE: to build this container image, you need web-ui source in .frontend directory
# on host machine, git clone it:
#     git clone https://github.com/KustoszApp/web-ui.git .frontend
# or bind-mount, if you already have it cloned elsewhere:
#     sudo mount --bind /path/to/kustosz/web-ui/ .frontend

# {{{ base image
FROM python:3.9-bullseye as base

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        netcat-openbsd \
        wait-for-it \
        supervisor \
        redis \
        jq \
        nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --home-dir /opt/kustosz -m --shell /bin/bash -U kustosz
# }}}

# {{{ build frontend
FROM base as frontendbuilder

RUN apt-get update && \
    apt-get install -y --no-install-recommends npm

RUN npm install --prefix /opt/kustosz-node-readability -g kustosz-node-readability

ENV BUILDDIR=/opt/kustosz-frontend-build/
COPY ./.frontend $BUILDDIR
WORKDIR $BUILDDIR
RUN npm install
RUN npm run build
# }}}

# {{{ build backend
FROM base as backendbuilder

USER kustosz

ENV SETUPTOOLS_USE_DISTUTILS="stdlib"
ENV BUILDDIR=/opt/kustosz/
ENV PATH="/opt/kustosz/.local/bin:$PATH"

WORKDIR $BUILDDIR

RUN pip install --no-cache --upgrade pip
RUN pip install --no-cache poetry==1.1.12

COPY pyproject.toml poetry.lock $BUILDDIR
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-interaction --no-dev --no-root -E container

COPY --chown=kustosz:kustosz . $BUILDDIR
RUN rm -rf $BUILDDIR/.frontend/
RUN poetry build
# }}}

# {{{ build production image
FROM base as release

USER kustosz

ENV SETUPTOOLS_USE_DISTUTILS="stdlib"
ENV HOME=/opt/kustosz/
ENV PATH="$HOME/.local/bin:$PATH"
ENV APP_HOME="$HOME/web"
ENV VIRTUAL_ENV="$HOME/.venv/"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV ENV_FOR_DYNACONF="production"
ENV DJANGO_SETTINGS_MODULE=kustosz.settings


RUN python -m venv $VIRTUAL_ENV
RUN mkdir -p $HOME/.local/
RUN mkdir -p $HOME/.config/kustosz
RUN mkdir -p $HOME/supervisor/logs
RUN mkdir -p $HOME/supervisor/run
RUN mkdir -p $APP_HOME/db
RUN mkdir -p $APP_HOME/static
RUN mkdir -p $APP_HOME/staticfiles
RUN mkdir -p $APP_HOME/mediafiles

COPY --chown=kustosz:kustosz --from=frontendbuilder /opt/kustosz-frontend-build/dist/ $APP_HOME/staticfiles/
COPY --chown=kustosz:kustosz --from=frontendbuilder /opt/kustosz-node-readability/ $HOME/.local/
COPY --chown=kustosz:kustosz --from=backendbuilder /opt/kustosz/.venv $VIRTUAL_ENV
COPY --chown=kustosz:kustosz --from=backendbuilder /opt/kustosz/dist/kustosz*.whl $HOME/wheels/
RUN pip install --no-cache --upgrade pip wheel
RUN pip install --no-cache --find-links $HOME/wheels/ kustosz[container]

COPY --chown=kustosz:kustosz ./settings.yaml $VIRTUAL_ENV/lib/python3.9/site-packages/settings.yaml

COPY --chown=kustosz:kustosz ./etc/supervisor/supervisord.conf $HOME/supervisor/supervisord.conf
COPY --chown=kustosz:kustosz ./etc/supervisor/redis.conf $HOME/supervisor/redis.conf

COPY --chown=kustosz:kustosz ./containers/entrypoint.prod.sh $HOME/entrypoint.sh

WORKDIR $HOME
EXPOSE 8000
VOLUME $APP_HOME/db
VOLUME $HOME/.config/kustosz

ENTRYPOINT [ "/opt/kustosz/entrypoint.sh" ]
# }}}
