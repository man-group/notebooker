from pymongo import MongoClient

from notebooker.serialization.mongo import NotebookResultSerializer


class PyMongoNotebookResultSerializer(NotebookResultSerializer):
    def __init__(
        self,
        user=None,
        password=None,
        database_name="notebooker",
        mongo_host="localhost",
        result_collection_name="NOTEBOOK_OUTPUT",
        **kwargs,
    ):
        self.user = user or None
        self.password = password or None
        super(PyMongoNotebookResultSerializer, self).__init__(database_name, mongo_host, result_collection_name)

    def get_mongo_database(self):
        return MongoClient(self.mongo_host, username=self.user, password=self.password).get_database(self.database_name)
