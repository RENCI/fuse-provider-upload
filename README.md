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

## use this template:

Note, a service must specify a pluginType, so for the purpose of this demonstration we use type 'p' (for data 'Provider')
* To add a new repository to the RENCI organization, [click here](https://github.com/organizations/RENCI/repositories/new) and select this repo for the template, otherwise the new repo will be added to your username.
* Clone your new repo using the 'recursive' tag (see below)
```
git clone --recursive http://github.com/RENCI/<your-repo-name>
```
* Make sure the tests pass (`./up.sh; prove` - see "validate installation" below to install test harness dependencies)
* Edit this README.md file and replace all occurrences of `fuse-provider-template` with your repo's name
* Update the source files appropriately:
 - [ ] **config/server-info.json**: describe your service's pluginType ["p":"Provider", "m":"Mapper", "t":"Tool"], required parameters, and supported/required objectVariables. Add anything required by GA4GH's DRS API
 - [ ] **docker-compose.yml**: replace `fuse-provider-template` with your repo's name and customize accordingly
 - [ ] **requirements.txt**: add your *version-locked* library requirements to the list
 - [ ] **sample.env**: add any required environmental variables, don't forget to also document them in this readme
 - [ ] **main.py**: 
   - [ ] Search for all occurrences of `fuse-provider-template` and replace
   - [ ] Define and add endpoints for your service
   - [ ] Create functions in ./lib to support you endpoints, with unit tests, adding the unit tests to github actions (examples coming soon!)
 - [ ] **write and run tests against the deployed containers - look at t/*.t for examples
 - [ ] contact the dockerhub/txscience organization administrator (email:txscience@lists.renci.org) to add a dockerhub repo for your container, if needed
* remove this section from the README.md
* checkin your mods to a branch and issue a pull request

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
