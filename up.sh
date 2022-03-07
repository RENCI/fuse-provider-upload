#!/bin/bash

export $(cat .env|grep -v '^#')
sudo chown -R ${USER} data
if [ `docker network ls | awk '{print $2}'|grep -w fuse` ] ;
then
    echo "found fuse, joining network";
else
    echo "creating and joining fuse network";
    docker network create -d bridge fuse
fi
docker-compose -f docker-compose.yml up --build -V -d
