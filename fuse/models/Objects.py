from typing import List

from fuse_cdm.main import Checksums, Contents, AccessMethods, as_form
from pydantic import BaseModel


@as_form
class ProviderExampleObject(BaseModel):  # xxx customize this code
    id: str = "string"
    name: str = "string"
    self_uri: str = "drs://drs.example.org/314159"
    size: int = 0
    created_time: str = "2022-02-04T05:28:01.648Z"
    updated_time: str = "2022-02-04T05:28:01.648Z"
    version: str = "string"
    mime_type: str = "application/json"
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
    description: str = "string"
    aliases: List[str] = ["string"]
