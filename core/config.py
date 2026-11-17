import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    opensearch_host: str = Field(default="http://localhost:9200", alias="OPENSEARCH_HOST")
    opensearch_use_ssl: bool = Field(default=False, alias="OPENSEARCH_USE_SSL")
    opensearch_verify_certs: bool = Field(default=False, alias="OPENSEARCH_VERIFY_CERTS")
    opensearch_username: str = Field(default="", alias="OPENSEARCH_USERNAME")
    opensearch_password: str = Field(default="", alias="OPENSEARCH_PASSWORD")
    opensearch_index_prefix: str = Field(default="logccino-logs", alias="OPENSEARCH_INDEX_PREFIX")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    debug: bool = Field(default=True, alias="DEBUG")

    llm_provider: str = Field(default="", alias="LLM_PROVIDER")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: Optional[str] = Field(default=None, alias="OPENAI_BASE_URL")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    default_model: str = Field(default="", alias="DEFAULT_MODEL")

    @model_validator(mode="after")
    def resolve_llm_defaults(self):
        # 1. 모델 결정: DEFAULT_MODEL 또는 LLM_MODEL
        if self.default_model and not self.llm_model:
            self.llm_model = self.default_model
        elif not self.llm_model:
            if self.openai_api_key:
                self.llm_model = "gpt-6-luna"
            else:
                self.llm_model = "gemini-2.5-flash"

        # 2. 프로바이더 결정: OPENAI_API_KEY가 있고 GEMINI_API_KEY가 없으면 자동으로 openai 선택
        if not self.llm_provider:
            if self.openai_api_key and not self.gemini_api_key:
                self.llm_provider = "openai"
            elif self.gemini_api_key:
                self.llm_provider = "gemini"
            elif self.openai_api_key:
                self.llm_provider = "openai"
            else:
                self.llm_provider = "gemini"
        elif self.llm_provider == "gemini" and not self.gemini_api_key and self.openai_api_key:
            # gemini 키가 없는데 openai 키가 있는 경우 자동 전환
            self.llm_provider = "openai"

        return self

settings = Settings()
