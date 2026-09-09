"""Direct loopback Ollama embedding transport for Chroma."""

from chromadb.api.types import Documents, EmbeddingFunction
from chromadb.utils.embedding_functions import register_embedding_function
from ollama import Client

from occupational_fitness_rag.llm import require_local_url


@register_embedding_function
class LocalOllamaEmbedding(EmbeddingFunction[Documents]):
    def __init__(self, url, model_name, timeout=60):
        self.url = require_local_url(url)
        self.model_name = model_name
        self.timeout = timeout
        self.client = Client(host=self.url, timeout=timeout, trust_env=False)

    def __call__(self, input):
        return self.client.embed(model=self.model_name, input=input).embeddings

    @staticmethod
    def name():
        return "fitness_local_ollama"

    def default_space(self):
        return "cosine"

    def get_config(self):
        return {"url": self.url, "model_name": self.model_name, "timeout": self.timeout}

    @staticmethod
    def build_from_config(config):
        return LocalOllamaEmbedding(**config)

    def validate_config_update(self, old_config, new_config):
        if old_config != new_config:
            raise ValueError("Embedding configuration changes require a new collection")
