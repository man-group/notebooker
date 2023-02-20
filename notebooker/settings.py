from typing import Dict

from dataclasses import dataclass, asdict

from notebooker.constants import DEFAULT_SERIALIZER, DEFAULT_MAILFROM_ADDRESS, DEFAULT_RUNNING_TIMEOUT


@dataclass
class BaseConfig:
    # The name of the kernel which we are using to execute notebooks.
    NOTEBOOK_KERNEL_NAME: str = "notebooker_kernel"

    # The temporary directory which will contain the .ipynb templates which have been converted from the .py templates.
    # Defaults to a random directory in ~/.notebooker/templates.
    TEMPLATE_DIR: str = ""
    # The temporary directory which will contain the .ipynb templates which have been converted from the .py templates.
    # Defaults to a random directory in ~/.notebooker/output.
    OUTPUT_DIR: str = ""

    # The directory of the Notebook Templates checked-out git repository.
    PY_TEMPLATE_BASE_DIR: str = ""
    # The subdirectory within the Notebook Templates git repo which holds notebook templates.
    PY_TEMPLATE_SUBDIR: str = ""
    # A boolean flag to dictate whether we should pull from git master every time we try to run a report
    # or list the available templates.
    NOTEBOOKER_DISABLE_GIT: bool = False

    # The serializer class we are using for storage, e.g. PyMongoResultSerializer
    SERIALIZER_CLS: DEFAULT_SERIALIZER = None
    # The dictionary of parameters which are used to initialize the serializer class above
    SERIALIZER_CONFIG: Dict = None

    # Value used in the from header of emails sent by notebooker if the user doesn't pass one when running a notebook
    DEFAULT_MAILFROM: str = DEFAULT_MAILFROM_ADDRESS

    RUNNING_TIMEOUT: int = DEFAULT_RUNNING_TIMEOUT

    @classmethod
    def copy_existing(cls, existing: "BaseConfig"):
        return cls(**asdict(existing))

    @classmethod
    def from_superset_kwargs(cls, kwargs: dict):
        """ When we have too many kwargs but we want to use a subset containing the fields. """
        return cls(**{k: v for (k, v) in kwargs.items() if k in cls.__dataclass_fields__})


@dataclass
class WebappConfig(BaseConfig):
    LOGGING_LEVEL: str = "INFO"  # The logging level of the application
    DEBUG: bool = False  # Whether to auto-reload files. Useful for development.
    PORT: int = 11828  # The application port.

    # The temporary directory which will contain the .ipynb templates which have been converted from the .py templates.
    # Defaults to a random directory in ~/.notebooker/webcache.
    CACHE_DIR: str = ""

    SCHEDULER_MONGO_DATABASE: str = ""
    SCHEDULER_MONGO_COLLECTION: str = ""
    DISABLE_SCHEDULER: bool = False
    READONLY_MODE: bool = False
