FROM python:3.9-bullseye as base

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        supervisor \
        redis \
        jq \
        nodejs && \
    rm -rf /var/lib/apt/lists/*
# FIXME: we pull node to use kustosz-node-readability. but we never install that

# build frontend
FROM base as frontendbuilder

RUN apt-get update && \
    apt-get install -y --no-install-recommends npm

ENV BUILDDIR=/opt/kustosz-frontend-build/
RUN git clone https://github.com/KustoszApp/web-ui.git $BUILDDIR
WORKDIR $BUILDDIR
# FIXME: we should build from latest / specified tag
RUN npm install
RUN npm run build

# build backend
FROM base as backendbuilder

ENV SETUPTOOLS_USE_DISTUTILS="stdlib"
ENV BUILDDIR=/opt/kustosz-build/

WORKDIR $BUILDDIR

RUN pip install --no-cache --upgrade pip
RUN pip install --no-cache poetry==1.1.12

COPY . $BUILDDIR
RUN poetry build

# build production image
FROM base as release

RUN adduser --home /opt/kustosz kustosz && adduser kustosz kustosz

USER kustosz

ENV SETUPTOOLS_USE_DISTUTILS="stdlib"
ENV HOME=/opt/kustosz/
ENV APP_HOME="$HOME/web"
ENV VIRTUAL_ENV="$HOME/virtualenv/"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV ENV_FOR_DYNACONF="production"
ENV DJANGO_SETTINGS_MODULE=kustosz.settings

RUN python -m venv $VIRTUAL_ENV
RUN mkdir -p $HOME/supervisor/logs
RUN mkdir -p $HOME/supervisor/run
RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/staticfiles
RUN mkdir $APP_HOME/mediafiles

COPY --from=frontendbuilder /opt/kustosz-frontend-build/dist/ $APP_HOME/staticfiles/
COPY --from=backendbuilder /opt/kustosz-build/dist/kustosz*.whl $HOME/wheels/
RUN pip install --no-cache --upgrade pip
RUN pip install --no-cache $HOME/wheels/* redis

COPY ./settings*yaml $VIRTUAL_ENV/lib/python3.9/site-packages/

COPY ./etc/supervisor/supervisord.conf $HOME/supervisor/supervisord.conf
COPY ./etc/supervisor/redis.conf $HOME/supervisor/redis.conf

COPY ./containers/entrypoint.prod.sh $HOME/entrypoint.sh

WORKDIR $HOME

ENTRYPOINT [ "/opt/kustosz/entrypoint.sh" ]
