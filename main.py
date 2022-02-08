import os

from fastapi import FastAPI, Depends, Path, Query, Body
from fastapi.logger import logger
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from typing import List

from bson.json_util import dumps, loads

from fuse.models.Objects import Passports, ProviderExampleObject

app = FastAPI()

origins = [
    f"http://{os.getenv('HOSTNAME')}:{os.getenv('HOSTPORT')}",
    f"http://{os.getenv('HOSTNAME')}",
    "http://localhost:{os.getenv('HOSTPORT')}",
    "http://localhost",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import pathlib
import json


    
@app.get("/service-info", summary="Retrieve information about this service")
async def service_info():
    '''
    Returns information about the DRS service

    Extends the v1.0.0 GA4GH Service Info specification as the standardized format for GA4GH web services to self-describe.

    According to the service-info type registry maintained by the Technical Alignment Sub Committee (TASC), a DRS service MUST have:
    - a type.group value of org.ga4gh
    - a type.artifact value of drs

    e.g.
    ```
    {
      "id": "com.example.drs",
      "description": "Serves data according to DRS specification",
      ...
      "type": {
        "group": "org.ga4gh",
        "artifact": "drs"
      }
    ...
    }
    ```
    See the Service Registry Appendix for more information on how to register a DRS service with a service registry.
    '''
    service_info_path = pathlib.Path(__file__).parent / "service_info.json"
    with open(service_info_path) as f:
        return json.load(f)

    
# READ-ONLY endpoints follow the GA4GH DRS API, modeled below
# https://editor.swagger.io/?url=https://ga4gh.github.io/data-repository-service-schemas/preview/release/drs-1.2.0/openapi.yaml
    
@app.get("/objects/{object_id}", summary="Get info about a DrsObject.")
async def objects(object_id: str = Path(default="", description="DrsObject identifier"),
                  expand: bool = Query(default=False, description="If false and the object_id refers to a bundle, then the ContentsObject array contains only those objects directly contained in the bundle. That is, if the bundle contains other bundles, those other bundles are not recursively included in the result. If true and the object_id refers to a bundle, then the entire set of objects in the bundle is expanded. That is, if the bundle contains aother bundles, then those other bundles are recursively expanded and included in the result. Recursion continues through the entire sub-tree of the bundle. If the object_id refers to a blob, then the query parameter is ignored.")):
    '''
    Returns object metadata, and a list of access methods that can be used to fetch object bytes.
    '''
    example_object = ProviderExampleObject()
    return example_object.dict()

# xxx add value for passport example that doesn't cause server error
# xxx figure out how to add the following description to 'passports':
# the encoded JWT GA4GH Passport that contains embedded Visas. The overall JWT is signed as are the individual Passport Visas
@app.post("/objects/{object_id}", summary="Get info about a DrsObject through POST'ing a Passport.")
async def post_objects(object_id: str = Path(default="", description="DrsObject identifier"),
                       expand: bool = Query(default=False, description="If false and the object_id refers to a bundle, then the ContentsObject array contains only those objects directly contained in the bundle. That is, if the bundle contains other bundles, those other bundles are not recursively included in the result. If true and the object_id refers to a bundle, then the entire set of objects in the bundle is expanded. That is, if the bundle contains aother bundles, then those other bundles are recursively expanded and included in the result. Recursion continues through the entire sub-tree of the bundle. If the object_id refers to a blob, then the query parameter is ignored."),
                       passports: Passports = Depends(Passports.as_form)):
    '''
    Returns object metadata, and a list of access methods that can be
    used to fetch object bytes. Method is a POST to accomodate a JWT
    GA4GH Passport sent in the formData in order to authorize access.
    '''
    example_object = ProviderExampleObject()
    return example_object.dict()

@app.get("/objects/{object_id}/access/{access_id}", summary="Get a URL for fetching bytes")
async def get_objects(object_id: str=Path(default="", description="DrsObject identifier"),
                      access_id: str=Path(default="", description="An access_id from the access_methods list of a DrsObject")):
    '''
    Returns a URL that can be used to fetch the bytes of a
    DrsObject. This method only needs to be called when using an
    AccessMethod that contains an access_id (e.g., for servers that
    use signed URLs for fetching object bytes).
    '''
    return {
        "url": "http://localhost/object.zip",
        "headers": "Authorization: None"
    }

# xxx figure out how to add the following description to 'passports':
# the encoded JWT GA4GH Passport that contains embedded Visas. The overall JWT is signed as are the individual Passport Visas.
@app.post("/objects/{object_id}/access/{access_id}", summary="Get a URL for fetching bytes through POST'ing a Passport")
async def post_objects(object_id: str=Path(default="", description="DrsObject identifier"),
                       access_id: str=Path(default="", description="An access_id from the access_methods list of a DrsObject"),
                       passports: Passports = Depends(Passports.as_form)):
    '''
    Returns a URL that can be used to fetch the bytes of a
    DrsObject. This method only needs to be called when using an
    AccessMethod that contains an access_id (e.g., for servers that
    use signed URLs for fetching object bytes). Method is a POST to
    accomodate a JWT GA4GH Passport sent in the formData in order to
    authorize access.

    '''
    return {
        "url": "http://localhost/object.zip",
        "headers": "Authorization: None"
    }

