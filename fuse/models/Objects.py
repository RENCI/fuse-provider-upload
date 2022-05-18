import datetime
import inspect
import os

from pydantic import BaseModel
from typing import Type, Optional, List
from fastapi import File, UploadFile, Form, Depends, HTTPException, Query
from fuse_utilities.main import as_form, Checksums, AccessMethods
import traceback


class Contents(BaseModel):
    name: str="string"
    id: str="string"
    drs_uri: str="http://{g_host_name}:{g_host_port}/{g_container_name:{g_container_port}/files/example.zip"
    contents: List[str] = [
        "string"
    ]

@as_form
class ProviderExampleObject(BaseModel): # xxx customize this code
    id: str="string"
    name: str="string"
    self_uri: str="drs://drs.example.org/314159"
    size: int=0
    created_time: str="2022-02-04T05:28:01.648Z"
    updated_time: str="2022-02-04T05:28:01.648Z"
    version: str="string"
    mime_type: str="application/json"
    checksums: List[Checksums] = [
        {
            "checksum": "string",
            "type": "sha-256"
        }
    ]
    access_methods: List[AccessMethods] = [
        {
            "type": "s3",
            "access_url": {
                "url": "string",
                "headers": "Authorization: Basic Z2E0Z2g6ZHJz"
            },
            "access_id": "string",
            "region": "us-east-1"
        }
    ]
    contents: List[Contents] = [
        {
            "name": "string",
            "id": "string",
            "drs_uri": "drs://drs.example.org/314159",
            "contents": [
                "string"
            ]
        }
    ]
    description: str="string"
    aliases: List[str] = [ "string" ]



