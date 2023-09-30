from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    upload_dir: str = '/reframe-data/uploads/'


settings = Settings()