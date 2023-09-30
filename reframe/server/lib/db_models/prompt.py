#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
from datetime import datetime
from typing import Optional, Dict, List, Any, Annotated

# External Libraries
import json
from pydantic import BaseModel, Field
from enum import Enum, IntEnum
from pydantic.functional_validators import BeforeValidator

# Internal Libraries

from pydantic.types import UUID, Json
from uuid6 import uuid7

def transform_to_str_to_json(v: dict | None) -> dict:
    if v:
        if isinstance(v, str):
            v = json.loads(v)

    return v

ParsedDict = Annotated[dict, BeforeValidator(transform_to_str_to_json)]

class Prompt(BaseModel):
    id_: UUID = Field(alias="_id", default_factory=uuid7)
    output_column_name: str
    output_column_slug: str
    prompt_version: str | None
    input_column: str | None
    prompt: ParsedDict | List[ParsedDict] | None
    dataframe_id: UUID
    initiator_id: UUID
    namespace_id: UUID
    id_list: Optional[List[UUID]]
    limit: int | str | None
    prompt_text: Optional[str] = None
    sql_text_query: Optional[str] = None
    input_column: Optional[str] = None

