[![AppVeyor](https://img.shields.io/docker/cloud/build/txscience/fuse-provider-template?style=plastic)](https://hub.docker.com/repository/docker/txscience/fuse-provider-template/builds)

# fuse-provider-template

Clone this repo to create a new FUSE-style data provider service.

FUSE stands for "[FAIR](https://www.go-fair.org/)", Usable, Sustainable, and Extensible.

FUSE services can be run as a stand-alone appliance (see `up.sh` below) or as a plugin to a FUSE deployment (e.g., [fuse-immcellfie](http://github.com/RENCI/fuse-immcellfie)). FUSE services come in 3 flavors:
* provider: provides a common data access protocol to a digital object provider
* mapper: maps the data from a particular data provider type into a common data model with consistent syntax and semantics
* tool: analyzes data from a mapper, providing results and a specification that describes the data types and how to display them.

All "provider" type services will support the read-only DRS API endpoints from the GA4GH, this template contains all the required endpoints to facilitate compliance.

## prerequisites:
* python 3.8 or higher
* Docker 20.10 or higher
* docker-compose v1.28 a
* perl 5.16.3 or higher (for testing the install)
* cpan
* jq

Tips for updating docker-compose on Centos:

```
sudo yum install jq
VERSION=$(curl --silent https://api.github.com/repos/docker/compose/releases/latest | jq .name -r)
sudo mv /usr/local/bin/docker-compose /usr/local/bin/docker-compose.old-version
DESTINATION=/usr/local/bin/docker-compose
sudo curl -L https://github.com/docker/compose/releases/download/${VERSION}/docker-compose-$(uname -s)-$(uname -m) -o $DESTINATION
sudo chmod 755 $DESTINATION
```

## configuration

1. Get this repository:
`git clone --recursive http://github.com/RENCI/fuse-provider-template

2. Copy `sample.env` to `.env` and edit to suit your provider:
* __API_PORT__ pick a unique port to avoid appliances colliding with each other

## start
```
./up.sh
```

## validate installation

Simple test from command line

```
curl -X 'GET' 'http://localhost:${API_PORT}/service-info' -H 'accept: application/json' |jq -r 2> /dev/null

```
Install test dependencies:
```
cpan App::cpanminus
# restart shell
cpanm --installdeps .

```
Run tests:
```
prove
```
More specific, detailed test results:
```
prove -v  :: --verbose
```

## stop
```
./down.sh
```
