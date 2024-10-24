FROM python:3.10-slim

WORKDIR /application

RUN mkdir /application/config
COPY ./requirements.txt /application/requirements.txt
RUN pip install --no-cache-dir -r /application/requirements.txt

COPY ./main.py /application/main.py
COPY ./app /application/app

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8880
ENV APP_ENV=dev
CMD python main.py -H ${APP_HOST} -P ${APP_PORT} -E ${APP_ENV}
