import uvicorn
import datetime
import os
import shutil
import uuid
from multiprocessing import Process
from typing import List, Optional

import aiofiles
import pymongo

from fastapi import FastAPI, Depends, Path, Query, Body, File, UploadFile
from fastapi import  Form, HTTPException
from fastapi.logger import logger
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from bson.json_util import dumps, loads

import traceback

import zipfile

from fuse.models.Objects import Passports, ProviderExampleObject, Checksums
from logging.config import dictConfig
import logging
from fuse.models.Config import LogConfig

dictConfig(LogConfig().dict())
logger = logging.getLogger("fuse-provider-upload")
# https://stackoverflow.com/questions/63510041/adding-python-logging-to-fastapi-endpoints-hosted-on-docker-doesnt-display-api

g_host_name=os.getenv('HOST_NAME')
g_host_port=os.getenv('HOST_PORT')
g_container_network = os.getenv('CONTAINER_NETWORK')
g_container_name=os.getenv('CONTAINER_NAME')
g_container_port=os.getenv('CONTAINER_PORT')
app = FastAPI()

origins = [
    f"http://{g_host_name}:{g_host_port}",
    f"http://{g_host_name}",
    f"http://localhost:{g_host_port}",
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

import pymongo
#mongo_client = pymongo.MongoClient('mongodb://%s:%s@upload-tx-persistence:27018/test' % (os.getenv('MONGO_NON_ROOT_USERNAME'), os.getenv('MONGO_NON_ROOT_PASSWORD')))
#mongo_db = mongo_client["test"]
#mongo_db_datasets_column = mongo_db["uploads"]
mongo_client_str = os.getenv("MONGO_CLIENT")
logger.info(msg=f"[MAIN] connecting to {mongo_client_str}")
mongo_client = pymongo.MongoClient(mongo_client_str)

mongo_db = mongo_client.test
mongo_db_version = mongo_db.command({'buildInfo':1})['version']
mongo_db_major_version = mongo_client.server_info()["versionArray"][0]
mongo_db_minor_version = mongo_client.server_info()["versionArray"][1]
mongo_uploads=mongo_db.uploads

# mongo migration functions to support running outside of container with more current instance
def _mongo_insert(fn, coll, obj):
        if mongo_db_major_version < 4:
            logger.info(msg=f"[{fn}] using collection.insert")
            coll.insert(obj)
        else:
            logger.info(msg=f"[{fn}] using collection.insert_one")
            coll.insert_one(obj)

def _mongo_count(fn, coll, obj, projection):
    if mongo_db_major_version < 3 and mongo_db_minor_version < 7:
        logger.info(msg=f"[{fn}] mongodb version = {mongo_db_version}, use deprecated entry count function")
        entry = coll.find(obj, projection)
        num_matches= entry[0].count()
    else: 
        logger.info(msg=f"[{fn}] mongo_db version = {mongo_db_version}, use count_documents function")
        num_matches=coll.count_documents(obj)
    logger.info(msg=f"[{fn}]found ({num_matches}) matches")
    return num_matches
# end mongo migration functions
            

import pathlib
import json


def _file_path(object_id):
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    return os.path.join(local_path, f"{object_id}-data")

from enum import Enum
class DataType(str, Enum):
    geneExpression='dataset-geneExpression'
    # xxx to add more datatypes: expand this

def _valid_contents(data_type, contents_list):
    if data_type == DataType.geneExpression:
        for file in contents_list:
            if file["name"] not in ["geneBySampleMatrix.csv", "phenoDataMatrix.csv"]:
                raise Exception(f"[_valid_contents] Unknown file {file} for data-type: {data_type}")
    # xxx to add more datatypes: expand this
    else:
        raise Exception(f"[_valid_contents] Unknown data-type: {data_type}")
    return True
            
    
# API is described in:
# http://localhost:8083/openapi.json
# Therefore:
# This endpoint self-describes with:
# curl -X 'GET'    'http://localhost:8083/openapi.json' -H 'accept: application/json' 2> /dev/null |python -m json.tool |jq '.paths."/submit".post.parameters' -C |less
# for example, an array of parameter names can be retrieved with:
# curl -X 'GET'    'http://localhost:8083/openapi.json' -H 'accept: application/json' 2> /dev/null |python -m json.tool |jq '.paths."/submit".post.parameters[].name' 
@app.post("/submit", description="Submit a digital object to be stored by this data provider")
async def upload(submitter_id: str = Query(default=..., description="unique identifier for the submitter (e.g., email)"),
                 data_type: Optional[DataType] = Query(default="gene-expression-dataset", description="the type of data; options are: dataset-geneExpression, results-pca, results-cellularFunction. Only gene-expression-dataset is supported by this provider"),
                 description: Optional[str] = Query(default=None, description="optional description of this object"),
                 version: Optional[str] = Query(default="1.0", description="version of this object; objects should never be deleted unless data are redacted"),
                 aliases: Optional[str] = Query(default=None, description="optional list of aliases for this object"),
                 checksums: Optional[List] = Query(default=None, description="optional checksums for the object, enabling verification checking by clients; this is a json list of objects, each object contains 'checksum' and 'type' fields, where 'type' might be 'sha-256' for example."),
                 requested_object_id: str = Query(default=None, description="optional argument to be used by submitter to request an object_id; this could be, for example, used to retrieve objects from a 3rd party for which this endpoint is a proxy. The requested object_id is not guaranteed, enduser should check return value for final object_id used."),
                 client_file: UploadFile = File(...)):
    '''
    Please notes:
    - mime-type: All submitted files must be of mime-type "application/zip"
    - A data_type: of 'gene-expression-dataset' must be a zip containing files named geneBySampleMatrix.csv and phenoDataMatrix.csv. The former has entrez-gene ids on the columns and samples on the rows. There is no header. The latter has a header with arbitrary phenotype names on the columns and sample names on the rows. Row1 of phenoDataMatrix.csv corresponds to Column2 of geneBySampleMatrix.csv and so forth.
    - File status: will be set in the persistent database as 'started' when the upload begins, 'failed' if an exception is thrown', and 'finished' when complete, in accordance with redis job.status() codes.
    '''
    try:
        # xxx use _gen_object_id here, but first replace _mongo_count signature to remove {fn}, projection file-wide
        object_id = f"upload_{submitter_id}_{uuid.uuid4()}"
        if requested_object_id != None:
            entry = mongo_uploads.find({"object_id": requested_object_id},
                                       {"_id": 0, "object_id": 1})
            num_matches = _mongo_count("upload",mongo_uploads,{"object_id": requested_object_id},{})
            logger.info(msg=f"[upload]found ({num_matches}) matches for requested object_id={requested_object_id}")
            if num_matches == 0:
                object_id = requested_object_id

        logger.info(msg=f"[upload]object_id={object_id}")
        logger.info(msg=f"[upload]client file_name={client_file.filename}")

        drs_uri = f"drs:///{g_host_name}:{g_host_port}/{g_container_network}/{g_container_name}:{g_container_port}/{object_id}",
        logger.info(msg=f"[upload]drs_uri={drs_uri}")

        meta_data = {"object_id": object_id,
                     "id": object_id,
                     "name": client_file.filename,
                     "description": description,
                     "self_uri": drs_uri,
                     "size": None,
                     "created_time": datetime.datetime.utcnow(),
                     "updated_time": None,
                     "version": version,
                     "mime_type": None,
                     "aliases": aliases,
                     "checksums": checksums,
                     "access_methods": None,
                     "contents": None,
                     "data_type": data_type,
                     "submitter_id": submitter_id,
                     "file_type": data_type,
                     "status": "started",
                     "stderr": None
                     }
        logger.info(msg=f"[upload] new object metatdata = {meta_data}")
        row_id = mongo_uploads.insert_one(meta_data).inserted_id
        logger.info(msg=f"[upload] new row_id = {row_id}")

        local_path = _file_path(object_id)
        os.mkdir(local_path)
        logger.info(msg=f"[upload] localpath = {local_path}")
        file_path = os.path.join(local_path, client_file.filename)
        async with aiofiles.open(file_path, 'wb') as out_file:
            contents = await client_file.read()
            await out_file.write(contents)
        logger.info(msg=f"[upload] file upload done.")
        
        # For MIME types
        import magic
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(file_path)
        logger.info(msg=f"[upload] file type = {mime_type}")
        assert(mime_type == 'application/zip' or mime_type == 'application/csv' or mime_type == 'text/csv' or mime_type == 'text/plain')
        
        contents_list = []
        if mime_type == 'application/zip':
            logger.info(msg=f"[upload] reading zip = {file_path}")
            zip = zipfile.ZipFile(file_path)    
            for subfile_path in zip.namelist():
                logger.info(msg=f"[upload]   subfile_path = {subfile_path}")
                [path_head, subfile_name] = os.path.split(subfile_path)
                logger.info(msg=f"[upload]   subfile_name = {subfile_name}")
                subfile_drs_uri = f"{drs_uri}/{subfile_name}"
                logger.info(msg=f"[upload]   subfile_drs_uri={subfile_drs_uri}")
                file_obj = {}
                file_obj["id"] = subfile_name
                file_obj["name"] = subfile_name         
                file_obj["drs_uri"] = subfile_drs_uri
                file_obj["contents"] = None
                # full_path is format: archive_name/file_name
                file_obj["full_path"] = subfile_path
                # use full_path to extract from archive; e.g.:
                #   with zip.open(full_path) as f:
                #     f.read()
                contents_list.append(file_obj)

        assert _valid_contents(data_type, contents_list)

        mongo_uploads.update_one({"object_id": object_id},
                                 {"$set": {
                                     "size": os.path.getsize(file_path),
                                     "updated_time": datetime.datetime.utcnow(),
                                     "mime_type": mime_type,
                                     "contents": contents_list,
                                     "status": "finished"
                                 }})
        logger.info(msg=f"[upload] status of {object_id} updated to 'finished'")
        # maybe check here if the file is an archive, and if so, set the list of files attribute
        ret_val = {"object_id": object_id}
        logger.info(msg=f"[upload] Done. Returning: {ret_val}")
        return ret_val
    
    except Exception as e:
        # assume the upload failed and update the status accordingly
        mongo_uploads.update_one({"object_id": object_id},
                                 {"$set": {"start_date": datetime.datetime.utcnow(), "status": "failed"}})
        logger.info(msg=f"[upload] exception, setting upload status to failed for {object_id}")
        raise HTTPException(status_code=404, detail=f"! Exception {type(e)} occurred while running upload for ({object_id}), message=[{e}] \n! traceback=\n{traceback.format_exc()}")

# xxx check param defaults
# xxx add parameters for finding object_id's of specific data_types (e.g., result-pca or dataset-geneExpression (DataType.geneExpression), etc.
@app.get("/search/{submitter_id}", summary="Get infos for all the DrsObject for this submitter_id.")
async def objects_search(submitter_id: str = Path(default="", description="submitter_id of user that uploaded the archive")):
    try:
        logger.info(msg=f"[search] submitter_id:{submitter_id}")
        ret = list(map(lambda a: a, mongo_uploads.find({"submitter_id": submitter_id},
                                                       {"_id": 0, "object_id": 1})))
        logger.info(msg=f"[search] ret:{ret}")
        return ret
    
    except Exception as e:
        raise HTTPException(status_code=404,
                            detail=f"! Exception {type(e)} occurred while searching for ({object_id}), message=[{e}] \n! traceback=\n{traceback.format_exc()}")
                       

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
    info = ""
    stderr = ""
    
    ret_mongo=""
    ret_mongo_err=""
    try:
        logger.warn(msg=f"[delete] Deleting object_id: {object_id}")
        ret = mongo_uploads.delete_one({"object_id": object_id})
        #<class 'pymongo.results.DeleteResult'>
        delete_status = "deleted"
        if ret.acknowledged != True:
            delete_status = "failed"
            ret_mongo += "ret.acknoledged not True.\n"
            logger.error(msg=f"[delete] delete failed, ret.acknowledged ! = True")
        if ret.deleted_count != 1:
            # should never happen if index was created for this field
            delete_status = "failed"
            ret_mongo += f"Wrong number of records deleted ({ret.deleted_count})."
            logger.error(msg=f"[delete] delete failed, wrong number deleted, count[1]={ret.deleted_count}")
        ## xxx
        # could check if there are any remaining; but this should instead be enforced by creating an index for this columnxs
        # could check ret.raw_result['n'] and ['ok'], but 'ok' seems to always be 1.0, and 'n' is the same as deleted_count
        ##
        ret_mongo += f"Deleted count=({ret.deleted_count}), Acknowledged=({ret.acknowledged})."
    except Exception as e:
        logger.error(msg=f"[delete] Exception {type(e)} occurred while deleting {object_id} from database")
        ret_mongo_err += f"! Exception {type(e)} occurred while deleting {object_id} from database, message=[{e}] \n! traceback=\n{traceback.format_exc()}"
        delete_status = "exception"

    # Data are cached on a mounted filesystem, unlink that too if it's there
    logger.info(msg=f"[delete] Deleting {object_id} from file system")
    ret_os=""
    ret_os_err=""
    try:
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        local_path = os.path.join(local_path, f"{object_id}-data")
        logger.info(msg=f"[delete] removing tree ({local_path})")
        shutil.rmtree(local_path,ignore_errors=False)
    except Exception as e:
        logger.error(msg=f"[delete] Exception {type(e)} occurred while deleting {object_id} from filesystem")
        ret_os_err += f"! Exception {type(e)} occurred while deleting job from filesystem, message=[{e}] \n! traceback=\n{traceback.format_exc()}"
        delete_status = "exception"
    try:
        info = f"{ret_mongo}\n {ret_os}"
        stderr = f"{ret_mongo_err}\n {ret_os_err}"
        ret = {
            "status": delete_status,
            "info": info,
            "stderr": stderr
        }
        logger.info(msg=f"[delete] returning ({ret})")
        assert ret["status"] == "deleted"
        return ret
    except Exception as e:
        raise HTTPException(status_code=404,
                            detail=f"! Message=[{info}]   Error while deleting ({object_id}), status=[{delete_status}] stderr=[{stderr}]")

# xxx parse {object_id} for '/' - if found, retrieve a specific file from within the archive
@app.get("/files/{object_id}")
def get_file(object_id: str):
    try:
        file_path = _file_path(object_id)
        logger.info(msg=f"[get_file] Retrieving {object_id} at {file_path}")

        assert os.path.isdir(file_path)
        assert len(os.listdir(file_path)) >= 1
        
        def iterfile(file_path):
            for file in os.listdir(file_path):
                with open(os.path.join(file_path, file), mode="rb") as file_data:
                    yield from file_data

        entry = mongo_uploads.find({"object_id": object_id}, {"mime_type":1, "name":1})
        num_matches = _mongo_count("get_file", mongo_uploads, {"object_id": object_id}, {})
        assert num_matches == 1
        logger.info(msg=f"[get_file] total entries found = {num_matches}")
        file_name= entry[0]["name"]
        logger.info(msg=f"[get_file] filename = {file_name}")
        media_type = entry[0]["mime_type"]
        logger.info(msg=f"[get_file] media_type = {media_type}")
        response = StreamingResponse(iterfile(file_path), media_type=media_type)
        response.headers["Content-Disposition"] = "attachment; filename="+file_name
        return response
    except Exception as e:
        raise HTTPException(status_code=404,
                            detail=f"! Exception {type(e)} occurred while retrieving for ({object_id}), message=[{e}] \n! traceback=\n{traceback.format_exc()}")
             

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
    try:
        entry = mongo_uploads.find({"object_id": object_id})
        num_matches = _mongo_count("objects", mongo_uploads, {"object_id": object_id}, {})
        logger.info(msg=f"[objects] total found for [{object_id}]={num_matches}")
        assert num_matches == 1
        logger.info(msg=f"[objects] found Object[{object_id}]={entry[0]}")
        obj = entry[0]
        del obj['_id']
        # xxx how does this get validated?
        return obj

        #example_object = ProviderExampleObject()
        #return example_object.dict()
    except Exception as e:
        raise HTTPException(status_code=404,
                            detail="! Exception {type(e)} occurred while searching for ({object_id}), message=[{e}] \n! traceback=\n{traceback.format_exc()}")

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

if __name__=='__main__':
        uvicorn.run("main:app", host='0.0.0.0', port=int(os.getenv("HOST_PORT")), reload=True )
