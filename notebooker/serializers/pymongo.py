import click
from pymongo import MongoClient

from notebooker.constants import DEFAULT_MONGO_DB_NAME, DEFAULT_MONGO_HOST, DEFAULT_RESULT_COLLECTION_NAME
from notebooker.serialization.mongo import MongoResultSerializer


@click.command()
@click.option(
    "--mongo-db-name",
    default=DEFAULT_MONGO_DB_NAME,
    help="The mongo database name to which we will save the notebook result.",
)
@click.option(
    "--mongo-host", default=DEFAULT_MONGO_HOST, help="The mongo host/cluster to which we are saving notebook results."
)
@click.option("--mongo-user", default=None, help="The mongo username.")
@click.option("--mongo-password", default=None, help="The mongo password.")
@click.option(
    "--result-collection-name",
    default=DEFAULT_RESULT_COLLECTION_NAME,
    help="The name of the collection to which we are saving notebook results.",
)
def cli_options():
    pass


class PyMongoResultSerializer(MongoResultSerializer, cli_options=cli_options):
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
        super(PyMongoResultSerializer, self).__init__(database_name, mongo_host, result_collection_name)

    def get_mongo_database(self):
        return MongoClient(self.mongo_host, username=self.user, password=self.password).get_database(self.mongo_db_name)


name = PyMongoResultSerializer.get_name()
