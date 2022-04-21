import inspect
from enum import Enum
from typing import Type, List

from fastapi import Form
from pydantic import BaseModel


def as_form(cls: Type[BaseModel]):
    new_params = [
        inspect.Parameter(
            field.alias,
            inspect.Parameter.POSITIONAL_ONLY,
            default=(Form(field.default) if not field.required else Form(...)),
        )
        for field in cls.__fields__.values()
    ]

    async def _as_form(**data):
        return cls(**data)

    sig = inspect.signature(_as_form)
    sig = sig.replace(parameters=new_params)
    _as_form.__signature__ = sig
    setattr(cls, "as_form", _as_form)
    return cls


class PluginParameter(BaseModel):
    id: str
    title: str
    description: str
    value: str
    type: str
    format: str


class SampleVariable(BaseModel):
    id: str = "FUSE:ExampleId"
    title: str = "Demo sampleVariable"
    description: str = "This sample variable is for demonstration only. Replace this with variables your appliance supports for the digital objects in your system."
    type: str = "string"
    default: str = "example default value"


class Checksums(BaseModel):
    checksum: str
    type: str


class AccessURL(BaseModel):
    url: str = "string"
    headers: str = "Authorization: Basic Z2E0Z2g6ZHJz"


class AccessMethods(BaseModel):
    type: str = "s3"
    access_url: AccessURL = {
        "url": "string",
        "headers": "Authorization: Basic Z2E0Z2g6ZHJz"
    }
    access_id: str = "string"
    region: str = "us-east-1"


class Contents(BaseModel):
    name: str = "string"
    id: str = "string"
    drs_uri: str = "http://{g_host_name}:{g_host_port}/{g_container_name:{g_container_port}/files/example.zip"
    contents: List[str] = [
        "string"
    ]


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


@as_form
class Passports(BaseModel):
    expand: bool = False
    passports: List[str] = ["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJnYTRnaF9wYXNzcG9ydF92MSI6W119.JJ5rN0ktP0qwyZmIPpxmF_p7JsxAZH6L6brUxtad3CM"]


class DataType(str, Enum):
    geneExpression = 'class_dataset_expression'
    resultsPCATable = 'class_results_PCATable'
    resultsCellFieDetailScoringTable = 'class_results_CellFieDetailScoringTable'
    resultsCellFieScoreBinaryTable = 'class_results_CellFieScoreBinaryTable'
    resultsCellFieScoreTable = 'class_results_CellFieScoreTable'
    resultsCellFieTaskInfoTable = 'class_results_CellFieTaskInfoTable'
    # xxx to add more datatypes: expand this


class FileType(str, Enum):
    datasetGeneExpression = 'filetype_dataset_expression'
    datasetProperties = 'filetype_dataset_properties'
    datasetArchive = 'filetype_dataset_archive'
    resultsPCATable = 'filetype_results_PCATable'
    resultsCellFieDetailScoringTable = 'filetype_results_CellFieDetailScoringTable'
    resultsCellFieScoreBinaryTable = 'filetype_results_CellFieScoreBinaryTable'
    resultsCellFieScoreTable = 'filetype_results_CellFieScoreTable'
    resultsCellFieTaskInfoTable = 'filetype_results_CellFieTaskInfoTable'
    # xxx to add more datatypes: expand this
