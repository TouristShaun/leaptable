#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
from datetime import datetime, timezone

# External Libraries
from pprint import pformat

import json
from pydantic import BaseModel, validator, Field, field_validator
from pydantic.functional_validators import BeforeValidator
from pydantic.types import UUID
from uuid6 import uuid7

# Internal Libraries
from typing import Optional, Dict, List, Any, Annotated
from validators import uuid

def convert_datetime_to_iso_8601_with_z_suffix(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def transform_to_str_to_json(v: datetime) -> datetime:
    if v:
        if isinstance(v, str):
            v = json.loads(v)

    return v

ParsedDict = Annotated[dict, BeforeValidator(transform_to_str_to_json)]

class User(BaseModel):
    id_: UUID = Field(alias="_id", default_factory=uuid7)
    cr_: datetime = Field(alias="_cr", default_factory=datetime.utcnow)
    up_: datetime = Field(alias="_up", default_factory=datetime.utcnow)
    email: str
    name: str
    preferred_name: str | None = None
    nickname: str | None = None
    beta_access: bool = False
    email_verified: bool = False
    picture: str | None = None
    app_metadata: ParsedDict | None = {}
    user_metadata: ParsedDict | None = {}

    def __str__(self):
        return pformat(self.dict(), indent=4)

class LoginActivity(BaseModel):
    id_: UUID = Field(alias="_id", default_factory=uuid7)
    cr_: datetime = Field(alias="_cr", default_factory=datetime.utcnow)
    up_: datetime = Field(alias="_up", default_factory=datetime.utcnow)
    user_id: UUID
    auth0_id: str
    ip: str
    user_agent: str
    country: str
    subdivision: str
    city: str
    logins_count: int
    last_login: datetime = Field(default_factory=datetime.utcnow)
    client_id: str
    connection: str
    transaction_id: str
    meta: dict | None = None