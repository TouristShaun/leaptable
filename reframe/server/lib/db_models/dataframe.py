#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
from typing import Optional, Dict, List, Any, Annotated

# External Libraries
import json
from pydantic import BaseModel, Field
from enum import Enum, IntEnum
from pydantic.functional_validators import BeforeValidator

# Internal Libraries

from pydantic.types import UUID, Json
from uuid6 import uuid7

def transform_str_to_json(v: dict | None) -> dict:
    if v:
        if isinstance(v, str):
            v = json.loads(v)
        elif isinstance(v, list):
            print(type(v[0]))
            v = [json.loads(i) for i in v]

    return v

ParsedDict = Annotated[dict, BeforeValidator(transform_str_to_json)]

class DATA_TYPE(str, Enum):
    TEXT = 'TEXT'
    INTEGER = 'INTEGER'
    FLOAT = 'FLOAT'
    BOOLEAN = 'BOOLEAN'
    UUID = 'UUID'
    JSONB = 'JSONB'
    TIMESTAMPZ = 'TIMESTAMPZ'

class DISPLAY_FORMAT_TYPE(str, Enum):
    TEXT = 'TEXT'
    JSON = 'JSON'
    INTEGER = 'INTEGER'
    FLOAT = 'FLOAT'
    BOOLEAN = 'BOOLEAN'
    UUID = 'UUID'
    TIMESTAMPZ = 'TIMESTAMPZ'

class Blueprint(BaseModel):
    id_: UUID = Field(alias="_id", default_factory=uuid7)
    dataframe_id: UUID
    type: DATA_TYPE = DATA_TYPE.TEXT
    index: int = 0
    display_name: str
    display_format: DISPLAY_FORMAT_TYPE = DISPLAY_FORMAT_TYPE.TEXT
    slug: str
    system: bool
    sticky_left: bool = False
    hidden: bool = False
    ai_gen: bool = False
    sort: str | None = None
    sort_index: int | None = None
    wrap: bool = True
    width: int = 300
    group: bool = False
    sort_index: int | None = None


class Dataframe(BaseModel):
    id_: UUID = Field(alias="_id", default_factory=uuid7)
    namespace_id: UUID
    slug : str
    name : str
    table_name : str

class HistoryItem(BaseModel):
    id_: UUID = Field(alias="_id", default_factory=uuid7)
    namespace_id: UUID
    initiator_id: UUID
    dataframe_id: UUID
    job_id: UUID
    version: str
    initiator_type: str
    type: str
    item: ParsedDict | List[ParsedDict] | None = {}