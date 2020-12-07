# WARNING!
# Importing from pymongo.py anywhere else may completely break this!

import importlib
import inspect
import pkgutil

import notebooker.serializers


def find_serializers(pkg):
    serializers = {}
    for _, name, ispkg in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        module = importlib.import_module(name)
        szs = {cls: mod for (cls, mod) in inspect.getmembers(module, inspect.isclass) if mod.__module__ == name}
        serializers.update(szs)
    return serializers


ALL_SERIALIZERS = find_serializers(notebooker.serializers)
SERIALIZER_TO_CLI_OPTIONS = {k: v.cli_options for (k, v) in ALL_SERIALIZERS.items()}
