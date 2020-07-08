from dateutil.parser import parse
from werkzeug.routing import BaseConverter


class DateConverter(BaseConverter):
    """Extracts a date from the path and converts it to a DateTime using dateutil.parser"""

    def to_python(self, value):
        return parse(value)

    def to_url(self, value):
        return value.isoformat()
