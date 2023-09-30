#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries

# External Libraries
from loguru import logger

# Internal Libraries
from reframe.lib.models.llms.main import OpenAI
from reframe.lib.core.main import SingleActionChatAgent

# Global Variables
llm = OpenAI()

serp_agent = SingleActionChatAgent(
    name="serp",
    invoke_commands=[
        "google", "bing", "search", "google_search", "search_bing", "search_google"
    ],
    tool_list= [{
        "display_name": "SERP",
        "name": "serp",
        "id": "serp",
        "output": "serp_content"
    }],
    chat_template = [
        {"role": "system", "content": """
            Given the following content. Return the information asked without
            generating supperfluous text. Answer with as few words as possible.
            """
         },
        {"role": "user", "content": "{{serp_content}}"},
        {"role": "assistant",
         "content": "Thanks. I have understood the context. Please provide the prompt"},
        {"role": "user", "content": "{{llm_prompt}}"}
    ],
    llm=llm
)

if __name__ == "__main__":
    logger.info(f"🏁 Starting SERP agent")
    serp_agent.run()