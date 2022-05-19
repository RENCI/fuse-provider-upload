FROM python:3.10-buster

RUN apt-get update
RUN apt-get -y install apt-transport-https ca-certificates curl gnupg2 software-properties-common

EXPOSE 8083

COPY . /app
RUN pip install -r /app/requirements.txt
RUN pip install -i https://test.pypi.org/simple/ fuse-cdm==1.5.0

WORKDIR /app

CMD uvicorn main:app --host 0.0.0.0 --port 8083
