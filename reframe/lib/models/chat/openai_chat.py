#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
from os import environ as env
from time import sleep
from pprint import pformat, pprint

# External Libraries
import redis
from loguru import logger
import openai

# Internal Libraries
from reframe.lib.core.decor import with_cache
from reframe.lib.utils import fmt_payload

# Global Variables


openai.api_key = env.get('OPENAI_API_KEY')

CACHE_EXPIRATION_DURATION = 60 * 60 * 24 * 90 # 90 days
# Redis Cache
REDIS_CACHE_HOST=env.get('REDIS_CACHE_HOST', "localhost")
REDIS_PASSWORD=env.get('REDIS_PASSWORD')
red_cache = redis.StrictRedis(
    REDIS_CACHE_HOST, 6379, charset="utf-8",
    password=REDIS_PASSWORD, decode_responses=True)
# ------------------------------

@with_cache(prefix="reframe::fn-cache::agent-run::fn->openai_chat", ex=CACHE_EXPIRATION_DURATION)
async def openai_chat(messages, *args, **kwargs):
    num_retries = kwargs.pop('num_retries', 3)
    for i in range(num_retries):
        try:
            msg = fmt_payload(messages)

            logger.debug(f"Calling openai_chat with {msg}")
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            pprint(response)
            return response.to_dict()['choices'][0]["message"]["content"]
        except openai.error.RateLimitError as openai_rate_limit_error:
            if i == num_retries - 1:
                raise openai_rate_limit_error
            retry_in = 60 * (i+1)
            logger.warning(f"Rate limit error: {openai_rate_limit_error}. Retrying in {retry_in} seconds")
            sleep(retry_in)
        except Exception as e:
            logger.exception(e)
            return None

