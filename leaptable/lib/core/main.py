#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 Leaptable, Inc."

# Standard Libraries
import asyncio
import os
import json
from pprint import pprint, pformat

# External Libraries
import psycopg
import redis
from os import environ as env
import tiktoken
import jinja2
from dotenv import load_dotenv
from loguru import logger
from psycopg import sql
import openai

# Internal Libraries
from leaptable.lib.core import RedisStreamProcessor
from leaptable.lib.models.chat import openai_chat
from leaptable.lib.utils import fmt_payload
from leaptable.server.lib.db_connection import Database

# Global Variables
from leaptable.server.lib.db_models.namespace import PROCESSING_STATUS, Namespace

CACHE_EXPIRATION_DURATION = 60 * 60 * 24 * 90 # 90 days
TASK_EXPIRATION_DURATION = 60 * 60 * 24 * 2 # 48 Hours

REDIS_STREAM_HOST=os.environ.get('REDIS_STREAM_HOST', "localhost")
REDIS_CACHE_HOST=os.environ.get('REDIS_CACHE_HOST', "localhost")
REDIS_PASSWORD=os.environ.get('REDIS_PASSWORD')
red_stream = redis.StrictRedis(
    REDIS_STREAM_HOST, 6379, charset="utf-8",
    password=REDIS_PASSWORD, decode_responses=True)
red_cache = redis.StrictRedis(
    REDIS_STREAM_HOST, 6379, charset="utf-8",
    password=REDIS_PASSWORD, decode_responses=True)
openai.api_key = os.environ['OPENAI_API_KEY']
jinja_env = jinja2.Environment()
# ------------------------------

class SingleActionChatAgent(RedisStreamProcessor):
    def __init__(self, name, invoke_commands, chat_template, tool_list=[], tool_graph={}, *args, **kwargs):
        load_dotenv('.env')
        self.name = name
        self.invoke_commands = invoke_commands
        self.tool_graph = tool_graph
        self.tool_list = tool_list

        self.trace_db = {}
        self.data_db = {}
        self.namespace = {}
        self.reframe_db = Database()

        for _template in chat_template:
            _template["content"] = jinja_env.from_string(_template["content"])
        self.chat_template = chat_template

        super().__init__(instream_key=f"agent->{self.name}")

        self.new_event_loop = asyncio.new_event_loop()
        # self.new_event_loop.run_until_complete(self.connect_to_db())
        logger.info(f"Initialized LeapTable Agent [name={name} invoke_commands={invoke_commands}]")

    def __del__(self):
        logger.info(f"Deconstructed LeapTable Agent [name={self.name}]")
        self.new_event_loop.stop()
        # asyncio.run(self.disconnect_db())

    async def connect_to_db(self):
        self.reframe_db = Database()
        await self.reframe_db.connect()

    async def disconnect_db(self):
        await self.data_db_conn.close()
        await self.data_db_cursor.close()

    def plan(self):
        raise NotImplementedError

    def get_last_processed_message_id(self):
        last_processed_message_id = red_stream.get(self.last_processed_stream_key)
        if last_processed_message_id is None:
            last_processed_message_id = "0-0"

        return last_processed_message_id

    def set_last_processed_message_id(self, message_id):
        last_processed_message_id = self.get_last_processed_message_id()

        old_ts, old_seq = last_processed_message_id.split("-")
        old_ts, old_seq = int(old_ts), int(old_seq)

        new_ts, new_seq = message_id.split("-")
        new_ts, new_seq = int(new_ts), int(new_seq)

        if new_ts > old_ts:
            last_processed_message_id = message_id
        elif new_ts == old_ts and new_seq > old_seq:
            last_processed_message_id = message_id
        else:
            print("!!!")
            exit(3)

        red_stream.set(self.last_processed_stream_key, last_processed_message_id)

        return last_processed_message_id

    async def get_namespace(self, namespace_id):
        if namespace_id in self.namespace:
            return self.namespace[namespace_id]

        sql = f"SELECT * FROM namespace WHERE _id = '{namespace_id}'"

        db_namespace = await self.reframe_db.fetch_one(sql)

        if db_namespace is None:
            raise Exception(f"Namespace {namespace_id} not found")

        logger.debug(f'Got namespace {namespace_id} from DB')
        namespace = Namespace(**db_namespace)

        namespace.data_db  = Database(**namespace.data_db_params)
        await namespace.data_db.connect()

        namespace.trace_db  = Database(**namespace.trace_db_params)
        await namespace.trace_db.connect()

        self.namespace[namespace_id] = namespace

        return namespace

    # Send jobs to the agent tools.
    async def sow(self):
        last_processed_message_id = self.get_last_processed_message_id()
        # logger.debug(f"sow: stream_key: {self.instream_key}")
        l = red_stream.xread(count=5, streams={self.instream_key: last_processed_message_id}, block=500)

        # Iterate over the stream keys.
        for _k in l:
            stream_key, stream_messages = _k
            # Iterate over the message batch for that stream key.
            for _j in stream_messages:
                message_id, message_data = _j
                logger.debug(f"Received stream_key={stream_key}, message_id={message_id} message_data={pformat(message_data)}")
                tool_name = self.tool_list[0].get('name')

                tool_stream_key = f"leaptable::instream::tool->{tool_name}"

                payload = json.loads(message_data['payload'])
                prompt_text = message_data['prompt_text']
                output_column = message_data['output_column']
                table_name = message_data['table_name']
                correlation_id = payload.get('_id')
                namespace_id = message_data.get('namespace_id')

                namespace = await self.get_namespace(namespace_id)

                # Update status to PROCESSING
                item = await namespace.data_db.fetch_one(
                    f'SELECT * FROM {table_name} WHERE _id = %(_id)s', {'_id': correlation_id})
                elem = json.loads(item[output_column])
                elem['status'] = PROCESSING_STATUS.PROCESSING.value
                item = await namespace.data_db.execute(
                    f'UPDATE {table_name} SET {output_column} = %(elem)s WHERE _id = %(_id)s',
                    {'_id': correlation_id, 'elem': json.dumps(elem)})
                logger.debug(f"Updated status to PROCESSING for correlation_id={correlation_id} in table={table_name}")

                message = {
                    'payload': json.dumps(payload),
                    'correlation_id': correlation_id,
                    'agent': self.name,
                }

                logger.debug(f"Running NS: {namespace_id} tool->{tool_name} with payload->{(pformat(message))}")

                red_stream.xadd(tool_stream_key, message)

                task_key = f"leaptable::task-pending::agent->{self.name}::correlation_id->{correlation_id}"
                red_cache.set(
                    task_key,
                    json.dumps({}, default=str),
                    ex=CACHE_EXPIRATION_DURATION
                )

                prompt_text_key = f"leaptable::prompt-text::agent->{self.name}::correlation_id->{correlation_id}"
                red_cache.set(
                    prompt_text_key,
                    json.dumps({
                        "prompt_text": prompt_text,
                        "output_column": output_column,
                        "table_name": table_name,
                        "namespace_id": namespace_id,
                    }, default=str),
                    ex=CACHE_EXPIRATION_DURATION
                )

                self.last_sow_key_processed = message_id

                self.set_last_processed_message_id(message_id)

    # Gather results from the result stream and place them into a set.
    async def reap(self):
        tool_name = self.tool_list[0].get('name')

        # Iterate over all the tools and get their results.
        tool_stream_key_map = {}
        for tool in self.tool_list:
            tool_stream_key = f"leaptable::outstream::agent->{self.name}::tool->{tool.get('id')}"
            tool_stream_key_map[tool_stream_key] = 0
        l = red_stream.xread(count=3, streams=tool_stream_key_map, block=5)

        # Iterate over the stream keys.
        for stream_key, stream_messages in l:
            # Iterate over the message batch for that stream key.
            for message_id, message_data in stream_messages:
                red_stream.xdel(stream_key, message_id)

                correlation_id = message_data.get('correlation_id')
                payload = message_data.get('payload')

                logger.opt(ansi=True).info(f"Received result from tool->{tool.get('id')}. correlation_id->{correlation_id}, payload-><yellow>{fmt_payload(payload)}</yellow>")

                result_key = f"leaptable::memory::agent->{self.name}::tool->{tool_name}[0]::elem->{correlation_id}"

                self.on_tool_result(tool_name, correlation_id, payload)

                red_stream.set(result_key, json.dumps(message_data, default=str))


    async def collate(self):
        key_prefix = f"leaptable::task-pending::agent->{self.name}::correlation_id->*"
        for key in red_stream.scan_iter(key_prefix):
            correlation_id = key.split("::correlation_id->")[1]

            prompt_text_key = f"leaptable::prompt-text::agent->{self.name}::correlation_id->{correlation_id}"
            llm_prompt = red_cache.get(prompt_text_key)
            if llm_prompt:
                llm_prompt = json.loads(llm_prompt)

            tools_result_set_complete = True
            db_result = None
            tool_result_map = {}
            # Check if all tools have completed.
            for tool in self.tool_list:
                tool_output_template = tool.get('output')
                tool_key = tool.get('name')
                tool_results = red_stream.get(
                    f"leaptable::memory::agent->{self.name}::tool->{tool.get('id')}[0]::elem->{correlation_id}"
                )
                if tool_results is None:
                    tools_result_set_complete = False
                    break
                else:

                    tool_results = json.loads(tool_results)
                    payload = json.loads(tool_results.get('payload'))

                    # Check if the tool errored.
                    if payload.get('status').lower() == 'error':
                        logger.error(f"Tool->{tool_key} errored. correlation_id->{correlation_id}")
                        tools_result_set_complete = False
                        db_result = payload
                        red_stream.delete(key)
                        break

                tool_result_map[tool_output_template] = tool_results

            if tools_result_set_complete:
                prompt_text = llm_prompt.get('prompt_text')

                if "$GPT" in prompt_text:
                    prompt_text = prompt_text.split("$GPT")[1]

                tool_result_map['llm_prompt'] = prompt_text

                enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

                formated_template = []

                for _template in self.chat_template:
                    formated_content = _template["content"].render(tool_result_map)
                    tokenized = enc.encode(formated_content)

                    tokenized = tokenized[:3500]
                    tokenized_text = enc.decode(tokenized)

                    formated_template.append(
                        {"content": tokenized_text, "role": _template["role"]}
                    )

                # Call OpenAI API.
                # response = await openai_chat(formated_template)
                response = await openai_chat(formated_template, read_cache=False, write_cache=True)
                # TODO: Check that the result is indeed a success.
                db_result = {
                    "status": PROCESSING_STATUS.SUCCESS.value,
                    "result": response
                }

                red_stream.delete(key)

                logger.debug(f"openai Result-->> {pformat(response)}")

                result_key = f"leaptable::agent-results::agent->{self.name}::correlation_id->{correlation_id}"
                red_cache.set(result_key, response, ex=CACHE_EXPIRATION_DURATION)

            if db_result:
                # Store results in Redis and Postgres.
                output_column = llm_prompt.get('output_column')
                table_name = llm_prompt.get('table_name')
                namespace_id = llm_prompt.get('namespace_id')
                namespace = await self.get_namespace(namespace_id)

                # TODO
                # Probably call a on_db_write hook here.

                try:
                    logger.info(f"Inserting into table {table_name}. {output_column}⇨ {pformat(db_result)}")
                    await namespace.data_db.execute(f"""
                        INSERT INTO {table_name} (_id, {output_column})
                        VALUES (%(_id)s, %(result)s)
                        ON CONFLICT (_id)
                        DO UPDATE SET
                        {output_column}=EXCLUDED.{output_column};"""
                    , {
                        "_id": correlation_id,
                        "result": json.dumps(db_result)
                    })
                except Exception as e:
                    logger.error(e)
                    logger.error(f"Error inserting into table {table_name}.")


    def on_tool_result(self, tool_name, correlation_id, payload):
        pass
        # Potentially raise a NotImplementedError here.

    def on_plan(self, plan):
        logger.debug(f"@on_plan Started plan->{plan}")

    async def wait_func(self, *args, **kwargs):
        await self.sow()
        await self.reap()
        await self.collate()

    def add_tool(self, tool):
        raise NotImplementedError

    def add_link(self, source, target):
        raise NotImplementedError

    def run(self, *args, **kwargs):
        self.new_event_loop = asyncio.new_event_loop()
        try:
            while True:
                self.new_event_loop.run_until_complete(self.wait_func())
        except redis.exceptions.ConnectionError as redis_connection_error:
            logger.critical(
                f"Redis connection error: {redis_connection_error}. Is Redis running and variable 'REDIS_STREAM_HOST' set?")
        except Exception as e:
            logger.exception(e)
        finally:
            self.new_event_loop.close()