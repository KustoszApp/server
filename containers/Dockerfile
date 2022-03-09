# vim: fdm=marker

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

RUN adduser --home /opt/kustosz kustosz && adduser kustosz kustosz

# FIXME: we pull node to use kustosz-node-readability. but we never install that
# }}}

# {{{ build frontend
FROM base as frontendbuilder

RUN apt-get update && \
    apt-get install -y --no-install-recommends npm

ENV BUILDDIR=/opt/kustosz-frontend-build/
RUN git clone https://github.com/KustoszApp/web-ui.git $BUILDDIR
WORKDIR $BUILDDIR
# FIXME: we should build from latest / specified tag
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

COPY . $BUILDDIR
RUN poetry build
# }}}

# {{{ build production image
FROM base as release

USER kustosz

ENV SETUPTOOLS_USE_DISTUTILS="stdlib"
ENV HOME=/opt/kustosz/
ENV APP_HOME="$HOME/web"
ENV VIRTUAL_ENV="$HOME/.venv/"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV ENV_FOR_DYNACONF="production"
ENV DJANGO_SETTINGS_MODULE=kustosz.settings

RUN python -m venv $VIRTUAL_ENV
RUN mkdir -p $HOME/.config/kustosz
RUN mkdir -p $HOME/supervisor/logs
RUN mkdir -p $HOME/supervisor/run
RUN mkdir -p $APP_HOME/db
RUN mkdir -p $APP_HOME/static
RUN mkdir -p $APP_HOME/staticfiles
RUN mkdir -p $APP_HOME/mediafiles

COPY --from=frontendbuilder /opt/kustosz-frontend-build/dist/ $APP_HOME/staticfiles/
COPY --from=backendbuilder /opt/kustosz/.venv $VIRTUAL_ENV
COPY --from=backendbuilder /opt/kustosz/dist/kustosz*.whl $HOME/wheels/
RUN pip install --no-cache --upgrade pip wheel
RUN pip install --no-cache --find-links $HOME/wheels/ kustosz[container]

COPY ./settings.yaml $VIRTUAL_ENV/lib/python3.9/site-packages/settings.yaml

COPY ./etc/supervisor/supervisord.conf $HOME/supervisor/supervisord.conf
COPY ./etc/supervisor/redis.conf $HOME/supervisor/redis.conf

COPY ./containers/entrypoint.prod.sh $HOME/entrypoint.sh

WORKDIR $HOME
EXPOSE 8000
VOLUME $APP_HOME/db
VOLUME $HOME/.config/kustosz

ENTRYPOINT [ "/opt/kustosz/entrypoint.sh" ]
# }}}
