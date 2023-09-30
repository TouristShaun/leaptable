#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
from pathlib import Path
from random import sample
import configparser
from os import environ as os_env

# External Libraries
from loguru import logger
from reframe.server.lib.db_models.user import User
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient
import sendgrid
from pprint import pprint, pformat

# Internal Libraries
from reframe.server.lib.db_models.dataframe import Blueprint, DISPLAY_FORMAT_TYPE, DATA_TYPE


# Global Variables
SLACK_BOT_TOKEN = os_env.get("SLACK_BOT_TOKEN")
SENDGRID_API_KEY = os_env.get("SENDGRID_API_KEY")
slack_client = WebClient(token=SLACK_BOT_TOKEN)

bp_template = {
    "type": "TEXT",
    "hidden": False,
    "ai_gen": False,
    "prompt_id": None,
    "width": 300,
    "pinned": False,
    "sticky_left": False,
    "selected": False,
    "system": False,
    "sort": None,
    "wrap": False,
    "sort_order": None,
    "filter": None,
    "filter_value": None,
    "group": None
}

def send_slack_message(channel_id: str, user: User, geo_ip: dict, user_agent: str, ip: str):
    """Send a message to slack"""
    try:
        cityName = geo_ip.get('cityName', "--")
        subdivisionName = geo_ip.get('subdivisionName', "--")
        countryName = geo_ip.get('countryName', "--")

        # Call the conversations.list method using the WebClient
        result = slack_client.chat_postMessage(
            channel=channel_id,
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{user.nickname}",
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✉️ \t{user.email}\n"
                                f"📍 \t{cityName}, {subdivisionName}, {countryName}\n"
                                f"📇 \t{ip}"
                    },
                    "accessory": {
                        "type": "image",
                        "image_url": user.picture,
                        "alt_text": f"{user.nickname} picture"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "plain_text",
                            "text": f"🖥️ \t{user_agent}",
                            "emoji": True
                        }
                    ]
                }
            ],
            text = f"New login from {user.nickname}. \n {user.email} \n {cityName}, {subdivisionName}, {countryName} \n {ip}"
        )

        logger.info(f"Message sent to slack channel {channel_id}")

    except SlackApiError as e:
        logger.error(f"Error posting message: {e}")

def create_system_bp():
    blueprint = []

    schema = dict(bp_template)
    schema["name"] = "_id"
    schema["slug"] = "_id"
    schema["system"] = True
    schema["hidden"] = True
    schema["type"] = DATA_TYPE.UUID
    schema["display_as"] = DISPLAY_FORMAT_TYPE.UUID
    blueprint.append(schema)

    schema = dict(bp_template)
    schema["name"] = "_cr"
    schema["slug"] = "_cr"
    schema["system"] = True
    schema["hidden"] = True
    schema["type"] = DATA_TYPE.TIMESTAMPZ
    schema["display_as"] = DISPLAY_FORMAT_TYPE.TIMESTAMPZ
    blueprint.append(schema)

    schema = dict(bp_template)
    schema["name"] = "_up"
    schema["slug"] = "_up"
    schema["system"] = True
    schema["hidden"] = True
    schema["type"] = DATA_TYPE.TIMESTAMPZ
    schema["display_as"] = DISPLAY_FORMAT_TYPE.TIMESTAMPZ
    blueprint.append(schema)

    return blueprint

def generate_random_emoji():
    emoji = sample(
        [
            "👗", "🪢", "📦", "🪀", "🚜", "🎣", "🧚🏾‍♂️", "🌋", "💠", "🛍️",
            "🌬", "💓", "🛣", "🌳", "🏄", "🔇", "🏇", "🐯", "🗻", "🗑", "📶", "🎬", "⭐️", "🐻", "🔘", "🚭",
            "☎", "🕴", "⚪️", "🎼", "🖖", "📇", "🐆", "🔕", "😧", "🍉", "💸", "🅾️", "🔮", "😅", "💚", "👴",
            "♉", "🔨", "🖕", "🌹", "🕝", "👔", "⁉", "🎊", "🏍", "📏", "🙌", "📭", "🕊", "😌", "🤔", "🎒",
            "🗞", "🐉", "🏚", "🆚", "🚺", "⛩", "🕶", "😁", "🔃", "👆", "⏯", "🎯", "🔌", "🧅", "🍦",
            "🛍", "👰", "🔱", "⏱", "✨", "❇", "💯", "😶", "🕦", "🕗", "🎗", "🌉", "😽", "🌏", "🔯", "🏞",
            "🚘", "◀", "😈", "🐸", "🐓", "👧", "❎", "🙀", "🖨", "🈶", "🏃", "📩", "👕", "🔻", "🌶", "💾",
            "🌆", "🎴", "🌴", "🎌", "🔼", "🏦", "🏨", "😜", "🎸", "🏛", "🆘", "🎃", "🕟", "🚫", "🍙",
            "🔲", "📻", "⏭", "😵", "💪", "🍲", "🕛", "🚧", "🛢", "👒", "🕓", "▪", "☹", "🤘", "🐄", "😞",
            "😓", "🚽", "🍨", "✅", "⛔", "🎧", "⛓", "🐟", "🍒", "💺", "📘", "💉", "🍭", "🍯", "🈵", "🚼",
            "☄", "📟", "🔎", "💟", "🐵", "🆎", "💫", "👷", "🌱", "🐷", "🖋", "🔷", "🚦", "☯", "🌠", "💦",
            "🛏", "⏳", "🐋", "📹", "🏺", "⏮", "➿", "⚰", "🏆", "🛬", "✔", "🛁", "🙆", "◻", "⚔", "🌰", "💭",
            "👈", "‼", "💠", "🖇", "💤", "💒", "👩", "⛎", "👣", "⌚", "🈯", "🗝", "🚷", "👪", "👁", "🎓",
            "🐈", "🔰", "💛", "🕥", "🕞", "🔑", "🏊", "🎻" "🚀", "🔼", "🕌", "💁", "➖", "🤐", "⏩", "🍆",
            "🚞", "🌲", "💿", "🍁", "🐛", "🕒", "🐤", "📂", "❤", "😛", "💫", "🎰", "📩", "🍣", "👬", "🐶",
            "🌰", "⚗", "🉑", "🍈", "😏", "🦀", "🐳", "⛳", "😌", "🙂", "🏁", "🍐", "🖥", "⬅", "📧", "⚛",
            "🙆", "🍉", "⁉", "🍧", "🚤", "🔘", "🈸", "🚒", "🍅", "😚", "🕛", "🈷", "⛰", "😣", "🌧", "🐝",
            "💰", "👈", "🆕", "🍵", "🚌", "🎶", "📒", "📣", "📈", "✉", "🔣", "🎖", "🎀", "😢", "⛺", "🛁",
            "🍦", "⛔", "💶", "🔷", "⬛", "✌", "🚟", "🐖", "↩", "♉", "✴", "🎽", "🍌",
            "🚊", "🍟", "⏬", "👰", "📤", "📪", "🐋", "🍛", "🌸", "💎", "😐", "📬", "🍻",
            "🕐", "🗽", "🐆", "🍮", "🕰", "🙍", "🔧", "🙋", "🐌", "🌿", "🏙", "🚈", "🏧",
            "🔲", "🎓", "😓", "📙", "🎫", "📜", "⏸", "😗", "🛂", "💞", "◻", "🆙", "🌚", "🔱",
            "🔉", "🔰", "🏏", "❄", "😪", "🌌", "🎳", "♑", "®", "🎏", "👧", "😳", "🌯", "🍗",
            "🐲", "🕍", "👂", "🏳", "🚘", "◾", "😺", "📚", "🛐", "🗂", "🌵", "💂", "🌽", "✍",
            "🎚", "🍹", "🚅", "☺", "🎅", "🚕", "⏪", "😙", "👡", "🏴", "👏", "🚿", "🏛", "🚚",
            "📗", "🏯", "🍨", "🔊", "🎈", "⚫", "🐑", "🎃", "⏹", "🍕", "💒", "〽", "🛫", "🚆",
            "🐚", "🍱", "🚹", "🖌", "🗄", "♠", "💄", "😱", "💬", "✋", "🛬", "🎻", "🍒", "🍊",
        ], 1)[0]

    return emoji


def send_email(message):
    # create our sendgrid client object, pass it our key, then send and return our response objects
    try:
        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email sent. Response tatus code {response.status_code}")
    except Exception as e:
        logger.exception(e)
        raise e from None

def extract_prompt_input_column_recursive(prompt, trigger):

    if isinstance(prompt, list):
        for elem in prompt:
            res = extract_prompt_input_column_recursive(elem, trigger)
            if res is not None:
                return res
    elif isinstance(prompt, dict):
        if 'children' in prompt:
            for elem in prompt["children"]:
                res = extract_prompt_input_column_recursive(elem, trigger)
                if res is not None:
                    return res
            if 'type' in prompt and prompt['type'] == 'mention':
                if trigger == prompt['trigger']:
                    return prompt['value']
        else:
            return None
    else:
        logger.error(f"Unknown type {type(prompt)} {prompt}")
    return None

def flatten_prompt(prompt):
    if isinstance(prompt, list):
        texts = []
        for elem in prompt:
            res = flatten_prompt(elem)
            if res is not None:
                texts.append(res)
        return " ".join(texts).strip()
    elif isinstance(prompt, dict):
        if 'children' in prompt:
            texts = []
            for elem in prompt["children"]:
                res = flatten_prompt(elem)
                if res is not None:
                    texts.append(res)
            if 'type' in prompt and prompt['type'] == 'mention':
                mention = f"{prompt['trigger']}{prompt['value']}"
                texts.append(mention)

            return " ".join(texts).strip()
        elif 'text' in prompt:
            return prompt['text']
        else:
            raise ValueError("Unknown prompt type")
    else:
        raise ValueError(f"Unknown type {type(prompt)}")
    return None