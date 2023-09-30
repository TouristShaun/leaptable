#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
from os import environ as os_env
from pprint import pprint

# External Libraries
from serpapi import GoogleSearch
from loguru import logger

# Internal Libraries
from reframe.lib.core.tool import Tool

# Global Variables
SERP_API_KEY = os_env.get("SERP_API_KEY")
assert SERP_API_KEY is not None, "SERP_API_KEY is not set"

class SerpTool(Tool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def exec(self, query, *args, **kwargs):
        assert query is not None, "Query is not set"
        logger.info(f"🔍 Searching Google {query}")
        search = GoogleSearch({
            "q": query,
            "api_key": SERP_API_KEY
        })
        result = search.get_dict()
        # result = result['organic_results']
        from pprint import pprint
        pprint(result)

        llm_result = {}
        if 'answer_box' in result:
            return result['answer_box']
        else:
            return result['organic_results']


        return result

if __name__ == "__main__":
    serp_tool = SerpTool(
        name="serp",
        invoke_commands=["serp_tool", "search", "google_search", "search_google"],
        read_cache=False,
        write_cache=True
    )
    logger.info(f"🏁 Starting SERP tool")
    serp_tool.run()