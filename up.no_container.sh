#!/bin/bash

# use this for debugging because
# WSL2 doesn't well support the '--network host' feature on docker

set -a
. .env
set +a

export MONGO_CLIENT=mongodb://localhost:${MONGO_PORT}/test
export REDIS_HOST=localhost
# store data one level up so docker build context doesn't find it
export RELATIVE_DATA_PATH=../no_container/fuse-provider-upload/data

python main.py
