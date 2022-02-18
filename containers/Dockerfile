# FIXME: build frontend here

# build backend
FROM python:3.9-bullseye as backendbuilder

ENV SETUPTOOLS_USE_DISTUTILS="stdlib"
ENV BUILDDIR=/opt/kustosz-build/

WORKDIR $BUILDDIR

RUN pip install --no-cache --upgrade pip
RUN pip install --no-cache poetry==1.1.12

COPY . $BUILDDIR
RUN poetry build

# build production image
FROM python:3.9-bullseye as release

RUN adduser --home /opt/kustosz kustosz && adduser kustosz kustosz

USER kustosz

ENV SETUPTOOLS_USE_DISTUTILS="stdlib"
ENV HOME=/opt/kustosz/
ENV APP_HOME="$HOME/web"
ENV VIRTUAL_ENV="$HOME/virtualenv/"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/staticfiles
RUN mkdir $APP_HOME/mediafiles

COPY --from=backendbuilder /opt/kustosz-build/dist/kustosz*.whl $HOME/wheels/
RUN python -m venv $VIRTUAL_ENV
RUN pip install --no-cache --upgrade pip
RUN pip install --no-cache $HOME/wheels/* redis

COPY ./settings.local.yaml ./settings.yaml $VIRTUAL_ENV/lib/python3.9/site-packages/
COPY ./containers/entrypoint.prod.sh $HOME/entrypoint.sh

WORKDIR $HOME

ENTRYPOINT [ "/opt/kustosz/entrypoint.sh" ]
