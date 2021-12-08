from typing import List, Union

from notebooker.constants import NotebookResultError, NotebookResultComplete
from notebooker.web.utils import get_serializer


def insert_fake_results(flask_app, results: List[Union[NotebookResultComplete, NotebookResultError]]):
    with flask_app.app_context() as ctx:
        serializer = get_serializer()
        for result in results:
            serializer.save_check_result(result)
