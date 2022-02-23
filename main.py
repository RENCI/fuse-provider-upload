import datetime
import os
import shutil
import uuid
from multiprocessing import Process
from typing import List

import aiofiles
import docker
import pymongo

from docker.errors import ContainerError
from fastapi import FastAPI, Depends, Path, Query, Body, File, UploadFile
from fastapi import  Form, HTTPException
from fastapi.logger import logger
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from bson.json_util import dumps, loads

import traceback

from fuse.models.Objects import Passports, ProviderExampleObject
from logging.config import dictConfig
import logging
from fuse.models.Config import LogConfig

dictConfig(LogConfig().dict())
logger = logging.getLogger("fuse-provider-upload")
# https://stackoverflow.com/questions/63510041/adding-python-logging-to-fastapi-endpoints-hosted-on-docker-doesnt-display-api

import pymongo
#mongo_client = pymongo.MongoClient('mongodb://%s:%s@upload-tx-persistence:27018/test' % (os.getenv('MONGO_NON_ROOT_USERNAME'), os.getenv('MONGO_NON_ROOT_PASSWORD')))
#mongo_db = mongo_client["test"]
#mongo_db_datasets_column = mongo_db["uploads"]
mongo_client = pymongo.MongoClient('mongodb://%s:%s@upload-tx-persistence:27017/test' % (os.getenv('MONGO_NON_ROOT_USERNAME'), os.getenv('MONGO_NON_ROOT_PASSWORD')))
mongo_db = mongo_client.test
mongo_uploads=mongo_db.uploads

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

# API is described in:
# http://localhost:8083/openapi.json
# Therefore:
# This endpoint self-describes with:
# curl -X 'GET'    'http://localhost:8083/openapi.json' -H 'accept: application/json' 2> /dev/null |python -m json.tool |jq '.paths."/submit".post.parameters' -C |less
# for example, an array of parameter names can be retrieved with:
# curl -X 'GET'    'http://localhost:8083/openapi.json' -H 'accept: application/json' 2> /dev/null |python -m json.tool |jq '.paths."/submit".post.parameters[].name' 
@app.post("/submit", description="Submit a digital object to be stored by this data provider")
async def upload(submitter_id: str = Query(default=None, description="unique identifier for the submitter (e.g., email)"),
                 requested_object_id: str = Query(default=None, description="optional argument to be used by submitter to request an object_id; this could be, for example, used to retrieve objects from a 3rd party for which this endpoint is a proxy. The requested object_id is not guaranteed, enduser should check return value for final object_id used."),
                 archive: UploadFile = File(...)):
    '''
    Parameters such as username/email for the submitter and parameter formats will be returned by the service-info endpoint to allow dynamic construction of dashboard elements
    '''
    try:
        object_id = "upload_" + submitter_id + "_" + str(uuid.uuid4())
        logger.info(msg=f"[upload]object_id="+str(object_id))
        row_id = mongo_uploads.insert_one(
            {"object_id": object_id, "submitter_id": submitter_id, "status": None, "stderr": None, "date_created": datetime.datetime.utcnow(), "start_date": None, "end_date": None}
        ).inserted_id
        logger.info(msg=f"[upload] new row_id = " + str(row_id))
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        local_path = os.path.join(local_path, f"{object_id}-data")
        os.mkdir(local_path)
        logger.info(msg=f"[upload] localpath = "+str(local_path))
        file_path = os.path.join(local_path, "upload.gz")
        logger.info(msg=f"[upload] filepath = "+str(file_path))
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await archive.read()
            await out_file.write(content)
        mongo_uploads.update_one({"object_id": object_id},
                                 {"$set": {"start_date": datetime.datetime.utcnow(), "status": "completed"}})
        ret_val = {"object_id": object_id}
        logger.info(msg=f"[upload] returning: " + str(ret_val))
        return ret_val
    except Exception as e:
        raise HTTPException(status_code=404,
                            detail="! Exception {0} occurred while running upload for ({1}), message=[{2}] \n! traceback=\n{3}\n".format(type(e), object_id, e, traceback.format_exc()))

# xxx check param defaults
@app.get("/objects/search/{submitter_id}", summary="Get infos for all the DrsObject for this submitter_id.")
async def objects_search(submitter_id: str = Path(default="", description="submitter_id of user that uploaded the archive")):
    try:
        logger.info(msg=f"[objects_search] submitter_id:" + str(submitter_id))
        ret = list(map(lambda a: a, mongo_uploads.find({"submitter_id": submitter_id},
                                                       {"_id": 0, "object_id": 1})))
        logger.info(msg=f"[objects_search] ret:" + str(ret))
        return ret
    except Exception as e:
        raise HTTPException(status_code=404,
                            detail="! Exception {0} occurred while searching for ({1}), message=[{2}] \n! traceback=\n{3}\n".format(type(e), e, traceback.format_exc(), object_id))
                       

@app.delete("/delete/{object_id}", summary="DANGER ZONE: Delete a downloaded object; this action is rarely justified.")
async def delete(object_id: str):
    '''
    Delete cached data from the remote provider, identified by the provided object_id.
    <br>**WARNING**: This will orphan associated analyses; only delete downloads if:
    - the data are redacted.
    - the system state needs to be reset, e.g., after testing.
    - the sytem state needs to be corrected, e.g., after a bugfix.

    <br>**Note**: If the object was changed on the data provider's server, the old copy should be versioned in order to keep an appropriate record of the input data for past dependent analyses.
    <br>**Note**: Object will be deleted from disk regardless of whether or not it was found in the database. This can be useful for manual correction of erroneous system states.
    <br>**Returns**: 
    - status = 'deleted' if object is found in the database and 1 object successfully deleted.
    - status = 'exception' if an exception is encountered while removing the object from the database or filesystem, regardless of whether or not the object was successfully deleted, see other returned fields for more information.
    - status = 'failed' if 0 or greater than 1 object is not found in database.
    '''
    delete_status = "done"

    # Delete may be requested while the download job is enqueued, so check that first:
    ret_job=""
    ret_job_err=""
    try:
        job = Job.fetch(object_id, connection=redis_connection)
        if job == None:
            ret_job="No job found in queue. \n"
        else:
            job = job.delete(remove_from_queue=True)
    except Exception as e:
        # job is not expected to be on queue so don't change deleted_status from "done"
        ret_job_err += "! Exception {0} occurred while deleting job from queue: message=[{1}] \n! traceback=\n{2}\n".format(type(e), e, traceback.format_exc())
                        
        delete_status = "exception"

    # Assuming the job already executed, remove any database records
    ret_mongo=""
    ret_mongo_err=""
    try:
        task_query = {"object_id": object_id}
        ret = mongo_uploads.delete_one(task_query)
        #<class 'pymongo.results.DeleteResult'>
        delete_status = "deleted"
        if ret.acknowledged != True:
            delete_status = "failed"
            ret_mongo += "ret.acknoledged not True.\n"
        if ret.deleted_count != 1:
            # should never happen if index was created for this field
            delete_status = "failed"
            ret_mongo += "Wrong number of records deleted ("+str(ret.deleted_count)+")./n"
        ## xxx
        # could check if there are any remaining; but this should instead be enforced by creating an index for this columnxs
        # could check ret.raw_result['n'] and ['ok'], but 'ok' seems to always be 1.0, and 'n' is the same as deleted_count
        ##
        ret_mongo += "Deleted count=("+str(ret.deleted_count)+"), Acknowledged=("+str(ret.acknowledged)+")./n"
    except Exception as e:
        ret_mongo_err += "! Exception {0} occurred while deleting job from database, message=[{1}] \n! traceback=\n{2}\n".format(type(e), e, traceback.format_exc())

        delete_status = "exception"
        
    # Data are cached on a mounted filesystem, unlink that too if it's there
    ret_os=""
    ret_os_err=""
    try:
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        local_path = os.path.join(local_path, object_id + f"-upload-data")
        
        shutil.rmtree(local_path,ignore_errors=False)
    except Exception as e:
        ret_os_err += "! Exception {0} occurred while deleting job from filesystem, message=[{1}] \n! traceback=\n{2}\n".format(type(e), e, traceback.format_exc())

        delete_status = "exception"

    ret_message = ret_job + ret_mongo + ret_os
    ret_err_message = ret_job_err + ret_mongo_err + ret_os_err
    return {
        "status": delete_status,
        "info": ret_message,
        "stderr": ret_err_message,
    }



# ----------------- GA4GH endpoints ---------------------
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

