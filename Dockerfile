FROM python:3.10-slim

WORKDIR /application

RUN mkdir /application/config
COPY ./requirements.txt /application/requirements.txt
RUN pip install --no-cache-dir -r /application/requirements.txt

COPY ./app /application/app

ARG APP_COMMIT_BRANCH=""
ARG APP_COMMIT_HASH=""
ARG APP_COMMIT_TIME=""
ARG APP_BUILD_TIME=""
ARG APP_BUILD_NUMBER=0

RUN touch config/versions.yaml
RUN echo "APP_COMMIT_BRANCH: \"$APP_COMMIT_BRANCH\"" >> config/versions.yaml
RUN echo "APP_COMMIT_HASH: \"$APP_COMMIT_HASH\"" >> config/versions.yaml
RUN echo "APP_COMMIT_TIME: \"$APP_COMMIT_TIME\"" >> config/versions.yaml
RUN echo "APP_BUILD_TIME: \"$APP_BUILD_TIME\"" >> config/versions.yaml
RUN echo "APP_BUILD_NUMBER: \"$APP_BUILD_NUMBER\"" >> config/versions.yaml

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8880
ENV APP_ENV=dev
CMD python app/main.py -H ${APP_HOST} -P ${APP_PORT} -E ${APP_ENV}
