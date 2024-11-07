FROM python:3.10-slim

WORKDIR /application

RUN mkdir /application/config
COPY ./requirements.txt /application/requirements.txt
RUN pip install --no-cache-dir -r /application/requirements.txt

COPY ./app /application/app

ARG APP_DEPLOY_NUMBER=0
ARG APP_COMMIT_TIME=""
RUN sed -i -e "s|\"|-$APP_DEPLOY_NUMBER $APP_COMMIT_TIME\"|2" app/version.py

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8880
ENV APP_ENV=dev
CMD python app/main.py -H ${APP_HOST} -P ${APP_PORT} -E ${APP_ENV}
