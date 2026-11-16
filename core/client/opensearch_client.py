from opensearchpy import OpenSearch
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class OpenSearchService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OpenSearchService, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        auth = None
        if settings.opensearch_username and settings.opensearch_password:
            auth = (settings.opensearch_username, settings.opensearch_password)

        self.client = OpenSearch(
            hosts=[settings.opensearch_host],
            http_auth=auth,
            use_ssl=settings.opensearch_use_ssl,
            verify_certs=settings.opensearch_verify_certs,
            ssl_show_warn=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        logger.info(f"Connected to OpenSearch at {settings.opensearch_host}")

    def ping(self) -> bool:
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"OpenSearch ping failed: {e}")
            return False

    def info(self) -> dict:
        return self.client.info()

    def get_client(self) -> OpenSearch:
        return self.client

opensearch_service = OpenSearchService()
