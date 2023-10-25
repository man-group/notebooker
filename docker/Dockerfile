FROM node:10.16.0-alpine as node_build

RUN set -eux \
  ; apk add git

COPY . /workspace

WORKDIR /workspace/notebooker/web/static
RUN set -eux \
  ; npm install \
  ; yarn bundle \
  ; ls -lah node_modules


FROM continuumio/anaconda3:2020.07-alpine as python_build

# this is needed for the a mongodb test fixture
USER root
RUN set -eux \
  ; echo 'http://dl-cdn.alpinelinux.org/alpine/v3.9/community' >> /etc/apk/repositories \
  ; echo 'http://dl-cdn.alpinelinux.org/alpine/v3.9/main' >> /etc/apk/repositories \
  ; apk update \
  ; apk add mongodb=4.0.5-r0 git

COPY --from=node_build /workspace /workspace

ENV PATH="/opt/conda/bin/:${PATH}"

WORKDIR /workspace

RUN set -eux \
  ; pip install -e ".[prometheus, test, docs]" \
  ; python -m ipykernel install --user --name=notebooker_kernel \
  ; pip install nbformat jupyter-core jupyter-client --upgrade \
  ; pip install -r ./notebooker/notebook_templates_example/notebook_requirements.txt \
  ; python setup.py develop \
  ; python setup.py build_sphinx \
  ; py.test tests \
  ; python setup.py bdist_wheel --universal


FROM continuumio/anaconda3
USER root

# Needed for PDF generation
RUN apt-get update && apt-get install -y git texlive-xetex

WORKDIR /app

COPY ./notebooker/notebook_templates_example/notebook_requirements.txt ./
COPY --from=python_build /workspace/dist/*.whl /app/

ENV PATH="/opt/conda/bin/:${PATH}"

RUN set -eux \
  ; python -m ipykernel install --user --name=notebooker_kernel \
  ; pip install -r ./notebook_requirements.txt ./notebooker-*.whl
