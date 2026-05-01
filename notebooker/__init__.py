from pkgutil import extend_path

from .version import __version__

__path__ = extend_path(__path__, __name__)
