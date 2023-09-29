#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 Leaptable, Inc."

# Standard Libraries
from typing import Annotated

# External Libraries
import uuid

import requests
from fastapi.encoders import jsonable_encoder

from leaptable.server.api.agents import single_action_chat_agent
from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body, UploadFile, status
from pprint import pprint, pformat

# Internal Libraries
from leaptable.server.lib.db_models.dataframe import Blueprint, DATA_TYPE, Dataframe, HistoryItem
from leaptable.server.lib.security import get_api_key
from leaptable.server.lib.db_models.namespace import Namespace
from leaptable.server.lib import hasura
from leaptable.server.lib.util import flatten_prompt, extract_prompt_input_column_recursive
from leaptable.server.lib.db_models.prompt import Prompt

router = APIRouter()

@router.post("/prompt/run/")
async def dataframe_upload(request: Request, namespace: Annotated[Namespace, Depends(get_api_key)], prompt: Prompt):
    """Upload dataframe endpoint"""
    print(prompt)

    try:
        limit = int(prompt.limit)
    except ValueError:
        if prompt.limit.lower() == 'all':
            limit = None
            id_list = []
            logger.info(f"Processing all IDs")
        elif prompt.limit.lower() == 'selected':
            limit = None
            id_list = prompt.id_list
            if id_list is None or len(id_list) == 0:
                logger.error(f"Selected ID list cannot be empty.")
                return {"error": "id_list cannot be empty."}, 400
            logger.debug(f"Processing selected ID list {len(id_list)}")
        else:
            logger.error(f"Invalid limit value {prompt.limit}")
            return {"error": "Invalid limit value"}, 400

    if prompt.output_column_name is None or prompt.output_column_slug is None:
        logger.error(f"Output column name and slug cannot be empty.")
        return {"error": "Output column name and slug cannot be empty."}, 400
    logger.info(
        f"Processing prompt {pformat(prompt.prompt)} with limit {limit} and output column [name={prompt.output_column_name} slug=({prompt.output_column_slug})]")

    # Retrieve the column names
    column_name = None
    if prompt.prompt_version == 'v1.0':
        input_column = extract_prompt_input_column_recursive(prompt.prompt, trigger='@')
        agent_key = extract_prompt_input_column_recursive(prompt.prompt, trigger='/')
        prompt.prompt_text = flatten_prompt(prompt.prompt)
    else:
        for prompt_obj in request.json['prompt']:
            assert prompt_obj['type'] == 'paragraph'
            filt_mention = list(filter(lambda x: 'type' in x and x['type'] == 'mention', prompt_obj['children']))

            # If there is no column mentioned, skip.
            if len(filt_mention) == 0:
                continue

            column_name = filt_mention[0]['column']

    if input_column is None:
        raise HTTPException

    logger.info(f"Input column name: '{input_column}' → output column '{prompt.output_column_slug}'. Prompt: '{prompt.prompt_text}'")

    db_dataframe = await request.app.state.meta_db.fetch_one(
        "SELECT * FROM dataframe WHERE _id = (%(_id)s)", {'_id': prompt.dataframe_id}
    )
    dataframe = Dataframe(**db_dataframe)

    # Add new output columns to the database
    await namespace.data_db.execute(
        f"""
        ALTER TABLE {dataframe.table_name} ADD COLUMN IF NOT EXISTS {prompt.output_column_slug} jsonb default '{{}}'::jsonb;
        """
    )

    # Retrieve elements from the Client DB table for the Column Prompt.
    if limit is not None:
        sql_text_query = f"""
        SELECT _id, {input_column} FROM {dataframe.table_name}
        LIMIT {limit}
        """
    elif len(id_list) > 0:
        sql_text_query = f"""
            SELECT _id, {input_column} FROM {dataframe.table_name}
            WHERE _id IN ({', '.join(map(lambda i: f"'{str(i)}'", id_list))})
            """
    else:
        sql_text_query = f"""
        SELECT _id, {input_column} FROM {dataframe.table_name}
        """
    logger.debug(f"SQL Query: {sql_text_query}")

    res = await single_action_chat_agent(request,
        {
            'input_column': prompt.input_column,
            'prompt_text': prompt.prompt_text,
            'sql_query_text': sql_text_query,
            'output_column': prompt.output_column_slug,
            'table': dataframe.table_name,
            'initiator_id': prompt.initiator_id,
            'initiator_type': 'user-web',
        }, namespace)

    print(res)

    job_id = res['data']['id_']

    # Get the blueprint for the dataframe.
    db_blueprint = await request.app.state.meta_db.fetch_list(
        "SELECT * FROM blueprint WHERE dataframe_id = (%(prompt.dataframe_id)s)", {'prompt.dataframe_id': prompt.dataframe_id}
    )
    bp_list = [Blueprint(**bp) for bp in db_blueprint]

    column_exists = len(list(filter(lambda bp: bp.slug == prompt.output_column_slug, bp_list))) > 0

    if not column_exists:
        logger.debug(f"Adding column {prompt.output_column_slug} to blueprint.")
        # If the column add operation succeeded, proceed to add it to the table blueprint.
        new_bp = Blueprint(
            display_name=prompt.output_column_name,
            display_format=DATA_TYPE.TEXT,
            slug=prompt.output_column_slug,
            system=False,
            ai_gen=True,
            dataframe_id=prompt.dataframe_id,
            type=DATA_TYPE.JSONB,
        )


        await request.app.state.meta_db.execute(
            f"""
            INSERT INTO blueprint (_id, display_name, slug, display_format, dataframe_id, ai_gen, system, type)
            VALUES (%(id_)s, %(display_name)s, %(slug)s, %(display_format)s, %(dataframe_id)s, %(ai_gen)s, %(system)s, %(type)s)
            ON CONFLICT (dataframe_id, slug) DO NOTHING;
            """, new_bp.dict()
        )

    hist = HistoryItem(**{
        "id_": prompt.id_,
        "item": {'prompt' : prompt.prompt},
        "version": "v1.01",
        "dataframe_id": prompt.dataframe_id,
        "namespace_id": namespace.id_,
        "initiator_id": prompt.initiator_id,
        "job_id": job_id,
        "initiator_type": "user-web",
        "type": "PROMPT"
    })

    from pprint import pprint
    pprint(jsonable_encoder(hist))

    # Write the history item
    await request.app.state.meta_db.execute(
        """
        INSERT INTO history (_id, item, version, dataframe_id, namespace_id, initiator_id, job_id, initiator_type, type)
        VALUES (%(_id)s, %(item)s, %(version)s, %(dataframe_id)s, %(namespace_id)s, %(initiator_id)s, %(job_id)s, %(initiator_type)s, %(type)s);
        """, jsonable_encoder(hist)
    )

    # Reload the table metadata on Hasura
    res = hasura.reload_table_metadata(connection_name=namespace.hasura_params['data_db'], table_name=dataframe.table_name)


    return {"status": "success", "message": "Dataframe uploaded successfully"}