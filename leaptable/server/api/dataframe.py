#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 Leaptable, Inc."

# Standard Libraries
from typing import Annotated
from pathlib import Path
import os
from os import environ as os_env

# External Libraries
import aiofiles
import boto3
import pandas as pd
from botocore.exceptions import ClientError, NoCredentialsError as BotoNoCredentialsError
from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, Request, Form, File, UploadFile, status
from sqlalchemy import create_engine

# Internal Libraries
from leaptable.server.lib.db_models.namespace import Namespace
from leaptable.server.lib.db_models.dataframe import Blueprint, DISPLAY_FORMAT_TYPE, DATA_TYPE
from leaptable.server.lib.config import settings
from leaptable.server.lib.security import get_api_key
from leaptable.server.lib import hasura
from leaptable.server.lib.util import bp_template, create_system_bp, generate_random_emoji

# Global Variables
from slugify import slugify
from uuid6 import uuid7
from werkzeug.utils import secure_filename

router = APIRouter()
S3_BUCKET=os_env.get('S3_BUCKET')

@router.post("/dataframe/upload/")
async def dataframe_upload(request: Request, namespace: Annotated[Namespace, Depends(get_api_key)],
                           file: Annotated[UploadFile, Form()]):
    """Upload dataframe endpoint"""

    # Get the namespace form the database
    namespace_short_id = str(namespace.id_).split("-")[3]
    namespace_path = f"{namespace_short_id}_{namespace.slug}"

    filename = secure_filename(file.filename)
    saved_file_path = os.path.join(settings.upload_dir, namespace_path, filename)
    Path(
        os.path.join(settings.upload_dir, namespace_path)
    ).mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(saved_file_path, 'wb') as out_file:
        while content := await file.read(1024):  # async read chunk
            await out_file.write(content)  # async write chunk
        logger.info(f"File saved to {saved_file_path}")

    try:
        # Upload to S3
        s3_client = boto3.client('s3')
        bucket_name = S3_BUCKET

        # TODO (PETER):
        # Create a file hash like so: https://stackoverflow.com/a/44873382
        s3_key = f'uploads/{filename}'
        bucket = s3_client.head_bucket(Bucket=bucket_name)

        s3_client.upload_file(saved_file_path, bucket_name, s3_key )
        logger.info(f"File uploaded to s3://{bucket_name}/{s3_key}")
    except ValueError as val_err:
        logger.error(val_err)
        logger.info("Ensure your AWS variables are set")
    except ClientError as e:
        logger.error(e)
    except BotoNoCredentialsError as no_creds:
        logger.warning("Missing or incorrect S3 Credentials provided. Skipping upload.")

    # Inspect file type and read as excel or csv.
    if saved_file_path.endswith(".csv"):
        logger.info("CSV file uploaded. Reading to pandas dataframe.")
        df = pd.read_csv(saved_file_path)
    elif file.content_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
        logger.info("Excel file uploaded. Reading to pandas dataframe.")
        df = pd.read_excel(saved_file_path, engine='openpyxl')
    elif file.content_type in ['application/vnd.ms-excel']:
        logger.info("Excel file uploaded. Reading to pandas dataframe.")
        df = pd.read_excel(saved_file_path, engine='openpyxl')
    else:
        logger.error(f"Unsupported file type {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsupported file type {file.content_type}. Only CSV and Excel files are supported."
        ) from None

    dataframe_id = str(uuid7())
    table_name = slugify(Path(filename).stem, separator='_')
    table_name = f"tb_{dataframe_id.split('-')[3]}_{table_name}"
    try:
        async with namespace.data_db.transaction() as data_db_conn:
            constraint_name = f"{table_name}_pk"

            await data_db_conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                _id             uuid                            default gen_random_uuid()   not null    constraint {constraint_name} primary key,
                _cr             timestamp   with time zone      default now()               not null,
                _up             timestamp   with time zone      default now()               not null
                );
            """)


            # Create the unique index on _id
            index_name = f"{table_name}__id_uindex"
            await data_db_conn.execute(f"""CREATE UNIQUE INDEX IF NOT EXISTS {index_name} on {table_name} (_id);""")
            logger.info("Created Table unique index")

            # Create the trigger to update _up
            trigger_name = f"{table_name}_update_datetime"
            await data_db_conn.execute(f"""
                CREATE TRIGGER {trigger_name}
                BEFORE UPDATE ON {table_name}
                FOR EACH ROW
                EXECUTE PROCEDURE moddatetime (_up);
                """
            )
            logger.info("Created Table moddatetime trigger")
            logger.info(f"End table {table_name} creation transaction")
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsupported file type {file.content_type}. {e}"
        ) from None

    try:

        blueprint = create_system_bp()

        # Create a blueprint for the table
        async with namespace.data_db.transaction() as data_db_conn:
            for column_name, column_type in df.dtypes.items():
                schema = dict(bp_template)
                col_slug = slugify(column_name, separator='_')

                df.rename(columns={f"{column_name}": f"{col_slug}"}, inplace=True, errors="raise")

                schema["name"], schema["slug"] = column_name, col_slug

                match column_type:
                    case "object":
                        schema["type"], schema["display_as"] = DATA_TYPE.TEXT.value, DISPLAY_FORMAT_TYPE.TEXT.value
                    case "int64":
                        schema["type"], schema["display_as"] = DATA_TYPE.INTEGER.value, DISPLAY_FORMAT_TYPE.INTEGER.value
                    case "float64":
                        schema["type"], schema["display_as"] = DATA_TYPE.FLOAT.value, DISPLAY_FORMAT_TYPE.FLOAT.value
                    case "bool":
                        schema["type"], schema["display_as"] = DATA_TYPE.BOOLEAN.value, DISPLAY_FORMAT_TYPE.BOOLEAN.value
                    case "datetime64[ns]":
                        schema["type"], schema["display_as"] = DATA_TYPE.TIMESTAMPZ.value, DISPLAY_FORMAT_TYPE.TIMESTAMPZ.value
                    case _:
                        logger.error(f"Unsupported column type {column_type}. Defaulting to TEXT.")
                        schema["type"], schema["display_as"] = DATA_TYPE.TEXT.value, DISPLAY_FORMAT_TYPE.TEXT.value

                await data_db_conn.execute(
                    f"""ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_slug} {schema['type']};"""
                )

                blueprint.append(schema)

        # Add _id column
        df.insert(0, '_id', [uuid7() for _ in range(len(df.index))])
        df.set_index('_id', inplace=True)

        # Recreate the DB url in the format that sqlalchemy expects.
        sqla_url = namespace.data_db.to_url_str()
        pg_engine = create_engine(sqla_url, echo=False)
        logger.info(f"Inserted dataframe into Data DB table {table_name}")

        df.to_sql(table_name, con=pg_engine, if_exists='append')

        # from pprint import pprint
        # pprint(blueprint)

        icon = generate_random_emoji()
        logger.info(f"Registering dataset {icon} {filename}")

        dataframe_id = str(uuid7())

        await request.app.state.meta_db.execute(f"""
            INSERT INTO dataframe (_id, name, slug, icon, namespace_id, table_name)
            VALUES (%(_id)s, %(name)s, %(slug)s, %(icon)s, %(namespace_id)s, %(table_name)s);
            """,
              {
                  "_id": dataframe_id,
                  "name": filename,
                  "slug": table_name,
                  "icon": icon,
                  "namespace_id": namespace.id_,
                  "table_name": table_name
              }
        )

        for _bp in blueprint:
            _blueprint = Blueprint(**{
                    "display_name": _bp["name"],
                    "display_format": _bp["display_as"],
                    "slug": _bp["slug"],
                    "system": _bp["system"],
                    "dataframe_id": dataframe_id,
                    "type": _bp["type"]
                })
            await request.app.state.meta_db.execute(
                """
                INSERT INTO blueprint (_id, display_name, slug, display_format, dataframe_id, system, type)
                VALUES (%(id_)s, %(display_name)s, %(slug)s, %(display_format)s, %(dataframe_id)s, %(system)s, %(type)s);
                """, _blueprint.dict())

    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsupported file type {file.content_type}. {e}"
        ) from None

    # Iterate over created_table_list and track the tables on hasura.
    # This is done to allow the tables to be queried via GraphQL.
    hasura_datadb = namespace.hasura_params["data_db"]
    logger.info(f"Registering table '{table_name} with hasura for connection '{hasura_datadb}'")
    res = hasura.track_table(connection_name=hasura_datadb, table_name=table_name)
    res = hasura.give_permission_to_user(connection_name=hasura_datadb, table_name=table_name)

    return {"status": "success", "message": "Dataframe uploaded successfully", "dataframe_id": dataframe_id}
