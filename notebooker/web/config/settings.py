from notebooker.serialization.serialization import Serializer


class BaseConfig:
    """ NB: This is an exhaustive list of all user-specifiable env vars. """

    PORT: int = 11828  # The application port.
    DATABASE_NAME: str = "notebooker"  # The mongo database which we are saving to
    RESULT_COLLECTION_NAME: str = "notebook_results"  # The mongo collection which we are saving to
    LOGGING_LEVEL: str = "INFO"  # The logging level of the application
    DEBUG: str = ""  # Whether to auto-reload files. Useful for development.

    # The temporary directory which will contain the .ipynb templates which have been converted from the .py templates.
    # Defaults to a random directory in ~/.notebooker/templates.
    TEMPLATE_DIR: str = ""
    # The temporary directory which will contain the .ipynb templates which have been converted from the .py templates.
    # Defaults to a random directory in ~/.notebooker/output.
    OUTPUT_DIR: str = ""
    # The temporary directory which will contain the .ipynb templates which have been converted from the .py templates.
    # Defaults to a random directory in ~/.notebooker/webcache.
    CACHE_DIR: str = ""

    # The name of the kernel which we are using to execute notebooks.
    NOTEBOOK_KERNEL_NAME: str = "notebooker_kernel"

    # A boolean flag to dictate whether we should pull from git master every time we try to run a report
    # or list the available templates.
    NOTEBOOKER_DISABLE_GIT: str = ""

    # The directory of the Notebook Templates checked-out git repository.
    PY_TEMPLATE_DIR: str = ""
    # The subdirectory within the Notebook Templates git repo which holds notebook templates.
    GIT_REPO_TEMPLATE_DIR: str = ""

    # --- Serializer-specific --- #
    NOTEBOOK_SERIALIZER: str = Serializer.PYMONGO.value  # The Serializer we are using as our backend storage.
    MONGO_HOST: str = "localhost"  # The environment to which pymongo is connecting.
    MONGO_USER: str = ""  # The username which we are connecting to pymongo with.
    MONGO_PASSWORD: str = ""  # The mongo user's password.


class DevConfig(BaseConfig):
    DATABASE_NAME: str = "notebooker-dev"


class ProdConfig(BaseConfig):
    MONGO_HOST: str = "a-production-mongo-cluster"
    DATABASE_NAME: str = "notebooker-prod"


class StagingConfig(BaseConfig):
    MONGO_HOST: str = "a-staging-mongo-cluster"
    DATABASE_NAME: str = "notebooker-staging"
