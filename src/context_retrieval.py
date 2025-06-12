from data_model.vespa_ai.vespa_client import VespaClient
from data_ingestion.text_embedder import Embedder
from dotenv import load_dotenv
from typing import List, Dict
from core.settings import VESPA_HOST, VESPA_PORT

load_dotenv()


class ContextRetrieval:

    def __init__(self):
        self.vespa_client = VespaClient(vespa_host=VESPA_HOST, vespa_port=VESPA_PORT)
        self.embedder = Embedder()

    def semantic_search(
            self,
            collection_name: str,
            query: str,
            ranking: str = 'embedding_query',
            hits: int = 50,
            target_hits: int = 50,
            restrictions: dict = None
    ) -> List[Dict]:
        """
        Build query for embedding fields and retrieve results

        :param collection_name: Collection to do the query on.
        :param query: User query/question (text) that needs to be embedded.
        :param ranking: Which ranking will be used.
        :param hits: Number of records that will be returned.
        :param target_hits: Wanted number of hits exposed to the real first-phase ranking function per content node.
        :param restrictions: Dictionary with additional filtering conditions.

        :return: Records that matches the query.
        """

        embedding = self.embedder.openai_embedding(text=query)

        query = {
            "hits": hits,
            "yql": f"select * from {collection_name} where "
                   f"({{targetHits: {target_hits}}}nearestNeighbor(embedding, query_embedding))",

            "ranking.features.query(query_embedding)": embedding,
            "ranking": ranking
        }

        if restrictions is not None:
            for k in restrictions:
                query['yql'] += f" and {k} contains '{restrictions[k]}'"

        return self.vespa_client.query(query_body=query)