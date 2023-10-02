#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
from os import environ as os_env
import json
from pprint import pprint, pformat
from time import time

# External Libraries
from psycopg import sql
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, Optional
from loguru import logger
import redis

from reframe.server.lib.db_connection import Database
from reframe.server.lib.db_models.namespace import Namespace, Job, PROCESSING_STATUS
from reframe.server.lib.security import get_api_key
from reframe.server.lib.db_models.agent import Agent

router = APIRouter()

REDIS_STREAM_HOST=os_env.get('REDIS_STREAM_HOST', "localhost")
REDIS_PASSWORD=os_env.get('REDIS_PASSWORD')
REDIS_USER=os_env.get('REDIS_USER')
red_stream = redis.StrictRedis(
    REDIS_STREAM_HOST, 6379, charset="utf-8", username=REDIS_USER,
    password=REDIS_PASSWORD, decode_responses=True)

from fastapi import Request

@router.post(
    "/agent/prompt/single_action_chat_agent/",
    name="Prompt agent",
    description="Invoke a single action chat agent",
)
async def single_action_chat_agent(
    request: Request,
    body: dict,
    namespace: Annotated[Namespace, Depends(get_api_key)]
):

    """Agent detail endpoint"""
    sql_query_text = body.get("sql_query_text")
    table_name = body.get("table")
    output_column = body.get("output_column")
    initiator_id = body.get("initiator_id")
    initiator_type = body.get("initiator_type")
    prompt = body.get("prompt")
    prompt_text = body.get("prompt_text")
    input_column = body.get("input_column")

    logger.debug(f"Prompt text: '{prompt_text}' Input column: '{input_column}' Output column: '{output_column}' sql_query_text: '{sql_query_text}'")

    job = Job(
        prompt=json.dumps(prompt),
        prompt_format_version="v0.0.1",
        initiator_id=initiator_id,
        initiator_type=initiator_type,
        read_cache=True,
        write_cache=True,
        table_name=table_name,
        input_params=json.dumps({
            "sql_query_text": sql_query_text,
            "input_column": input_column,
        }),
        output_params=json.dumps({
            "output_column": output_column,
        })
    )

    try:
        await namespace.trace_db.execute(
            """
            INSERT INTO trace.job (_id, prompt, table_name, prompt_format_version, initiator_id, initiator_type,
                        read_cache, write_cache, input_params, output_params)
            VALUES (%(id_)s, %(prompt)s, %(table_name)s,%(prompt_format_version)s, %(initiator_id)s, %(initiator_type)s,
                        %(read_cache)s, %(write_cache)s, %(input_params)s, %(output_params)s)
            """, job.dict())
        logger.info(f"Added job to DB {job.id_}")

    except Exception as e:
        logger.exception(e)

    # Determine agent type
    is_browser_agent = False
    is_serp_agent = False
    activation_command = None
    for key_word in ["browse", "visit"]:
        if f"/{key_word}" in prompt_text:
            is_browser_agent = True
            activation_command = f"/{key_word}"
            logger.debug(f"Activation command: {activation_command}")
            break

    for key_word in ["google_search", "search_google", "google", "search"]:
        if f"/{key_word}" in prompt_text:
            is_serp_agent = True
            activation_command = f"/{key_word}"
            logger.debug(f"Activation command: {activation_command}")
            break

    if is_browser_agent:
        stream_key = "reframe::instream::agent->browser"
    elif is_serp_agent:
        stream_key = "reframe::instream::agent->serp"
    else:
        raise Exception("Unknown agent type")

    logger.debug(f"Stream key: {stream_key}")

    # Fetch items from DB and add to stream
    items = await namespace.data_db.fetch_list(
        sql_query_text, {})

    record_count = 0
    for record in items:

        if is_browser_agent:
            payload = {
                "_id": str(record['_id']),
                "url": record[input_column]
            }
        elif is_serp_agent:
            serp_query = prompt_text.split(("."))[0].replace(activation_command, "")
            serp_query = serp_query.replace(f"@{input_column}", record[1])
            serp_query = serp_query.strip()

            payload = {
                "_id": str(record['_id']),
                "query": serp_query
            }
        else:
            raise Exception("Unknown agent type")

        stream_message = {
            'ts': time(),
            'payload': json.dumps(payload),
            'job_id': str(job.id_),
            'namespace_id': str(namespace.id_),
            "table_name": table_name,
            "prompt": json.dumps(prompt),
            "prompt_text": prompt_text,
            "output_column": output_column,
        }

        # Update status to QUEUED
        item = await namespace.data_db.fetch_one(
            f'SELECT * FROM {table_name} WHERE _id = %(_id)s', {'_id': record['_id']})
        elem = json.loads(item[output_column])
        elem['status'] = PROCESSING_STATUS.QUEUED.value
        item = await namespace.data_db.execute(
            f'UPDATE {table_name} SET {output_column} = %(elem)s WHERE _id = %(_id)s',
            {'_id': record['_id'], 'elem': json.dumps(elem)})

        red_stream.xadd(stream_key, stream_message)
        logger.opt(ansi=True).debug(f"Added elem to stream <b>{stream_key}</b>. Elem: <green>{pformat(stream_message)}</green>")
        record_count += 1
    logger.info(f"Added {record_count} elems to stream {stream_key}")

    return {"status": "success", 'data': job.dict()}