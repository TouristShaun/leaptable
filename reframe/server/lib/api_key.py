import uuid


def generate_api_key() -> str:
    api_token = uuid.uuid4().hex
    return f'sk_{api_token}'
