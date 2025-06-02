from typing import List

from openai import OpenAI

from core.config import EMBEDDING_MODEL


class Embedder:
    def __init__(self):
        self.openai_client = OpenAI()

    def openai_embedding(self, text: str, model: str = EMBEDDING_MODEL) -> List[float]:
        """
        Get the embedding of a text using OpenAI API.

        :param text: Text to be embedded.
        :param model: OpenAI model to be used for embedding.

        :return: List of floats representing the embedding of the text.
        """
        return (
            self.openai_client.embeddings.create(input=[text], model=model)
            .data[0]
            .embedding
        )