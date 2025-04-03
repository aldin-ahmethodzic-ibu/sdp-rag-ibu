from vespa.application import Vespa
from typing import Dict, Optional, List
from datetime import datetime
from requests.exceptions import HTTPError
import traceback


class VespaClient:

    _instances = {}

    def __new__(cls, vespa_host: str, vespa_port: int = 8080):
        """
        Singleton pattern to create a VespaClient instance for each Vespa instance.

        :param: vespa_host: Vespa host address.
        :param: vespa_port: Vespa host port, default is 8080.
        """

        if cls._instances.get(vespa_host) is None:

            cls._instances[vespa_host] = super().__new__(cls)
            instance = cls._instances[vespa_host]
            instance.app = Vespa(url=f"http://{vespa_host}:{vespa_port}")

        return cls._instances[vespa_host]

    def find_one(self, collection_name: str, record_id: str) -> Optional[Dict]:
        """
        Fetches the record with a given ID from the Vespa database.

        :param: collection_name: Name of the collection to fetch the record from.
        :param: record_id: ID of the record that needs to be fetched.

        :return: Dictionary with the entire record, or None if not found.
        """

        try:
            response = self.app.get_data(schema=collection_name, data_id=record_id)
        except HTTPError:
            return None

        if response.status_code == 200:
            return response.json
        else:
            raise Exception(f"Error while getting record with id {record_id}.\n\n{traceback.format_exc()}")

    def find_many(self, collection_name: str, record_ids: List[str]) -> List[Dict]:
        """
        Find multiple records from a given collection.

        :param: collection_name: Schema from which the records will be fetched.
        :param: record_ids: IDs of the records that needs to be fetched.

        :return: List of dictionaries with data. If no records were found, the empty list is returned.

        """

        if len(record_ids) == 0:
            return []

        result_set = []
        record_ids = [{"id": record_id} for record_id in record_ids]
        responses = self.app.get_batch(schema=collection_name, batch=record_ids)

        for idx, response in enumerate(responses):
            if response.status_code == 200:
                result_set.append(response.json)
            else:
                continue

        return result_set

    def insert_one(self, collection_name: str, record: Dict) -> None:
        """
        Inserts one record into the specified collection.

        :param: collection_name: Schema where the record will be inserted.

        :param: record:
            Data that will be inserted into database.

            Example of the valid record:
            {
                "id": "example_id",
                "fields": {
                    "field_1": "value_1",
                    ...
                    "field_n": "value_n"
                }
            }
        """

        record['fields']['created_at'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        record['fields']['updated_at'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        response = self.app.feed_data_point(schema=collection_name, data_id=record['id'], fields=record['fields'])

        if response.status_code != 200:
            raise Exception(f"Error while writing record with id {record['id']}.\n\n{traceback.format_exc()}")

    def insert_many(self, collection_name: str, records: List[Dict]):
        """
        Inserts multiple records in the given collection.

        :param: collection_name: Schema where the records will be inserted.
        :param: records: Records that will be inserted into database.

        Example of data:
        [
            {
                "id": "some_id",
                "fields": {
                    "field_1": "value_1",
                    ...
                    "field_n": "value_n"
                }
            },
            ...
            {...}
        ]
        """

        if len(records) == 0:
            return

        for data_dict in records:
            data_dict['fields']['created_at'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            data_dict['fields']['updated_at'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        responses = self.app.feed_batch(schema=collection_name, batch=records)

        for idx, response in enumerate(responses):
            if response.status_code != 200:
                raise Exception(f"Error while writing record with id {records[idx]['id']}\n\n{traceback.format_exc()}")

    def update_one(self, collection_name: str, record: Dict, upsert: bool = False):
        """
        Updates one record in the given collection.

        :param: collection_name: The name of the collection where the record will be updated.
        :param: record: Record that will be updated.

        :param: upsert:
            Boolean value which determines if the record is inserted in case it does not exist. If true, the value
            is inserted in case it didn't exist already.

        Example of data_dict:
        {
            "id": "some_id",
            "fields": {
                "field_1": "value_1",
                ...
                "field_n": "value_n"
            }
        }
        """

        record['create'] = upsert
        record['fields']['updated_at'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        response = self.app.update_data(
            schema=collection_name, data_id=record["id"], fields=record["fields"], create=record.get("create", False)
        )
        if response.status_code != 200:
            raise Exception(f"Error while updating record with id {record['id']}\n\n{traceback.format_exc()}")

    def update_many(self, collection_name: str, records: List[Dict], upsert: bool = False):
        """
        Updates multiple records in the given collection.

        :param: collection_name: Collection name where the records will be updated.
        :param: records: Records that will be updated.

        :param: upsert:
            Boolean value which determines if the record is inserted in case it does not exist. If true, the value
            is inserted in case it didn't exist already.

        Example of data:
        [{
            "id": "some_id",
            "fields": {
                "field_1": "value_1",
                ...
                "field_n": "value_n"
            }
        }]
        """

        if len(records) == 0:
            return

        for data_dict in records:
            data_dict['create'] = upsert
            data_dict['fields']['updated_at'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        responses = self.app.update_batch(schema=collection_name, batch=records)

        for idx, response in enumerate(responses):
            if response.status_code != 200:
                raise Exception(
                    f"Error while updating record with id {records[idx]['id']}.\n\n{traceback.format_exc()}"
                )

    def delete_one(self, collection_name: str, record_id: str):
        """
        Deletes one record from a given collection.

        :param: collection_name: Collection from which the record will be deleted,
        :param: record_id: ID of record that will be deleted.
        """

        response = self.app.delete_data(schema=collection_name, data_id=record_id)

        if response.status_code != 200:
            raise Exception(f"Error while deleting record with id {record_id}.\n\n{traceback.format_exc()}")

    def delete_many(self, collection_name: str, record_ids: List[str]):
        """
        Delete multiple records from a given collection.

        :param: collection_name: Collection from which the records will be deleted
        :param: record_ids:
            ID of the records that will be deleted. Example of record_ids:  ["example_id_1", "example_id_2"]
        """

        if len(record_ids) == 0:
            return

        record_ids = [{"id": record_id} for record_id in record_ids]
        responses = self.app.delete_batch(schema=collection_name, batch=record_ids)

        for idx, response in enumerate(responses):
            if response.status_code != 200:
                raise Exception(
                    f"Error while deleting record with id {record_ids[idx]['id']}.\n\n{traceback.format_exc()}"
                )

    def query(self, query_body: Dict) -> List[Dict]:
        """
        Send any YQL query and retrieve results.

        :param: query_body:
            Dictionary with the query body. The only required field within this dictionary is 'yql'.

            The example of the entire query_body:
            {
                "yql": "select * from resources where resource_id contains 'example_id'",
                "hits": 10
            }

            The examples of the valid YQL query are:
                # For string matching
                "select * from resources where resource_id contains 'example_id'"

                # Negation example
                "select * from resources where !(resource_id contains 'example_id')"

                # For bool and int matching
                "select resource_id, resource_type from resources where visible_on_app=true"

        :return: The list of records that match the query.
        """

        results = self.app.query(body=query_body)
        return results.hits
