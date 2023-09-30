#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
import json
from pydantic import BaseModel, Field, BeforeValidator
from datetime import datetime

# External Libraries
from pydantic import BaseModel
from pydantic.types import UUID, Json
from uuid6 import uuid7
from typing import Optional, Dict, List, Any, Annotated

def transform_str_to_json(v: dict | None) -> dict:
    if v:
        if isinstance(v, str):
            v = json.loads(v)
        elif isinstance(v, list):
            print(type(v[0]))
            v = [json.loads(i) for i in v]

    return v

ParsedDict = Annotated[dict, BeforeValidator(transform_str_to_json)]

class ApiKey(BaseModel):
    id_: UUID = Field(alias="_id", default_factory=uuid7)
    cr_: datetime = Field(alias="_cr", default_factory=datetime.utcnow)
    up_: datetime = Field(alias="_up", default_factory=datetime.utcnow)
    key: str
    name: str
    namespace_id: UUID
    usage_count: int
