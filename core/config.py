import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    opensearch_host: str = Field(default="http://localhost:9200", alias="OPENSEARCH_HOST")
    opensearch_use_ssl: bool = Field(default=False, alias="OPENSEARCH_USE_SSL")
    opensearch_verify_certs: bool = Field(default=False, alias="OPENSEARCH_VERIFY_CERTS")
    opensearch_username: str = Field(default="", alias="OPENSEARCH_USERNAME")
    opensearch_password: str = Field(default="", alias="OPENSEARCH_PASSWORD")
    opensearch_index_prefix: str = Field(default="logccino-logs", alias="OPENSEARCH_INDEX_PREFIX")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    debug: bool = Field(default=True, alias="DEBUG")

    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    llm_model: str = Field(default="gemini-2.5-flash", alias="LLM_MODEL")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
