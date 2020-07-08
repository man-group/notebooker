FROM node:10.16.0-alpine as node_build

RUN set -eux \
  ; apk add git

COPY . /workspace

WORKDIR /workspace/notebooker/web/static
RUN set -eux \
  ; yarn install --frozen-lockfile \
  ; yarn list --depth=0 \
  ; yarn run lint \
  ; ls -lah node_modules

FROM continuumio/anaconda3:latest as python_build

COPY --from=node_build /workspace /workspace

ENV PATH="/opt/conda/bin/:${PATH}"

WORKDIR /workspace
RUN set -eux \
  ; pip install -e ".[prometheus]" ".[test]" \
  ; python -m ipykernel install --user --name=notebooker_kernel \
  ; pip install -r ./notebook_templates/notebook_requirements.txt \
  ; python setup.py develop \
  ; python setup.py build_sphinx \
  ; py.test tests \
  ; python setup.py bdist_egg

FROM continuumio/anaconda3:latest

COPY --from=python_build /workspace/dist/*.egg /app/

WORKDIR /app
ENV VERSION=0.0.1

RUN echo 'http://dl-cdn.alpinelinux.org/alpine/v3.9/community' >> /etc/apk/repositories
RUN echo 'http://dl-cdn.alpinelinux.org/alpine/v3.9/main' >> /etc/apk/repositories
RUN apk update
RUN apk add mongodb=4.0.5-r0

RUN python -m ipykernel install --user --name=notebooker_kernel
RUN pip install -r ./notebook_templates/notebook_requirements.txt

RUN set -eux \
  ; . /root/.bashrc \
  ; pip install "notebooker-${VERSION}-py3.6.egg"