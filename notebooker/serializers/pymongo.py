import click
from pymongo import MongoClient

from notebooker.constants import DEFAULT_DATABASE_NAME, DEFAULT_MONGO_HOST, DEFAULT_RESULT_COLLECTION_NAME
from notebooker.serialization.mongo import MongoResultSerializer


@click.command()
@click.option(
    "--database-name",
    default=DEFAULT_DATABASE_NAME,
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
        mongo_user=None,
        mongo_password=None,
        database_name="notebooker",
        mongo_host="localhost",
        result_collection_name="NOTEBOOK_OUTPUT",
        **kwargs,
    ):
        self.mongo_user = mongo_user or None
        self.mongo_password = mongo_password or None
        super(PyMongoResultSerializer, self).__init__(database_name, mongo_host, result_collection_name)

    def get_mongo_database(self):
        return MongoClient(self.mongo_host, username=self.mongo_user, password=self.mongo_password).get_database(
            self.database_name
        )


name = PyMongoResultSerializer.get_name()
