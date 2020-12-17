import datetime
from logging import getLogger
from typing import Any, AnyStr, Dict, List, Optional, Tuple, Union, Iterator

import click
import gridfs
import pymongo
from gridfs import NoFile

from notebooker.constants import JobStatus, NotebookResultComplete, NotebookResultError, NotebookResultPending

logger = getLogger(__name__)
REMOVE_ID_PROJECTION = {"_id": 0}
REMOVE_PAYLOAD_FIELDS_PROJECTION = {"raw_html_resources": 0, "raw_html": 0, "raw_ipynb_json": 0}
REMOVE_PAYLOAD_FIELDS_AND_ID_PROJECTION = dict(REMOVE_PAYLOAD_FIELDS_PROJECTION, **REMOVE_ID_PROJECTION)


class MongoResultSerializer:
    # This class is the interface between Mongo and the rest of the application

    def __init__(self, database_name="notebooker", mongo_host="localhost", result_collection_name="NOTEBOOK_OUTPUT"):
        self.database_name = database_name
        self.mongo_host = mongo_host
        self.result_collection_name = result_collection_name
        mongo_connection = self.get_mongo_database()
        self.library = mongo_connection[result_collection_name]
        self.result_data_store = gridfs.GridFS(mongo_connection, "notebook_data")

    def __init_subclass__(cls, cli_options: click.Command = None, **kwargs):
        if cli_options is None:
            raise ValueError(
                "A MongoResultSerializer has been declared without cli_options. "
                "Please add them like so: `class MySerializer(cli_options=cli_opts)`."
            )
        cls.cli_options = cli_options
        super().__init_subclass__(**kwargs)

    def serializer_args_to_cmdline_args(self) -> List[str]:
        args = []
        for cli_arg in self.cli_options.params:
            if not hasattr(self, cli_arg.name):
                raise ValueError(
                    "The Serializer class must have attributes which are named the same as the click "
                    "options, e.g. --mongo-database should have a 'mongo_database' attribute"
                )
            opt, value = cli_arg.opts[0], getattr(self, cli_arg.name)
            if value is not None:
                args.extend([opt, value])
        return args

    @classmethod
    def get_name(cls):
        return cls.__name__

    def get_mongo_database(self):
        raise NotImplementedError()

    def _save_raw_to_db(self, out_data):
        out_data["update_time"] = datetime.datetime.now()
        existing = self.library.find_one({"job_id": out_data["job_id"]})
        if existing:
            self.library.replace_one({"_id": existing["_id"]}, out_data)
        else:
            self.library.insert_one(out_data)
        # Ensure that the job_id index exists
        self.library.create_index([("job_id", pymongo.ASCENDING)], background=True)
        self.library.create_index([("report_name", pymongo.ASCENDING)], background=True)
        self.library.create_index([("update_time", pymongo.DESCENDING)], background=True)
        self.library.create_index([("status", pymongo.ASCENDING), ("update_time", pymongo.DESCENDING)], background=True)

    def _save_to_db(self, notebook_result):
        out_data = notebook_result.saveable_output()
        self._save_raw_to_db(out_data)

    def update_stdout(self, job_id, new_lines):
        result = self.library.find_one_and_update({"job_id": job_id}, {"$push": {"stdout": {"$each": new_lines}}})
        return result

    def update_check_status(self, job_id: str, status: JobStatus, **extra):
        existing = self.library.find_one({"job_id": job_id})
        if not existing:
            logger.warning(
                "Couldn't update check status to {} for job id {} since it is not in the database.".format(
                    status, job_id
                )
            )
        else:
            existing["status"] = status.value
            for k, v in extra.items():
                existing[k] = v
            self._save_raw_to_db(existing)

    def save_check_stub(
        self,
        job_id: str,
        report_name: str,
        report_title: Optional[str] = "",
        job_start_time: Optional[datetime.datetime] = None,
        status: JobStatus = JobStatus.PENDING,
        overrides: Optional[Dict] = None,
        mailto: str = "",
        generate_pdf_output: bool = True,
        hide_code: bool = False,
    ) -> None:
        """ Call this when we are just starting a check. Saves a "pending" job into storage. """
        job_start_time = job_start_time or datetime.datetime.now()
        report_title = report_title or report_name
        pending_result = NotebookResultPending(
            job_id=job_id,
            status=status,
            report_title=report_title,
            job_start_time=job_start_time,
            report_name=report_name,
            mailto=mailto,
            generate_pdf_output=generate_pdf_output,
            overrides=overrides or {},
            hide_code=hide_code,
        )
        self._save_to_db(pending_result)

    def save_check_result(self, notebook_result: Union[NotebookResultComplete, NotebookResultError]) -> None:
        # Save to mongo
        logger.info("Saving {}".format(notebook_result.job_id))
        self._save_to_db(notebook_result)

        # Save to gridfs
        if isinstance(notebook_result, NotebookResultComplete):
            if notebook_result.raw_html_resources and "outputs" in notebook_result.raw_html_resources:
                for filename, binary_data in notebook_result.raw_html_resources["outputs"].items():  # type: ignore
                    self.result_data_store.put(binary_data, filename=filename, encoding="utf-8")
            if notebook_result.pdf:
                self.result_data_store.put(
                    notebook_result.pdf, filename=_pdf_filename(notebook_result.job_id), encoding="utf-8"
                )

    def _convert_result(
        self, result: Dict, load_payload: bool = True
    ) -> Union[NotebookResultError, NotebookResultComplete, NotebookResultPending, None]:
        if not result:
            return None

        status = result.get("status", "")
        job_status = JobStatus.from_string(status)
        if job_status is None:
            return None
        cls = {
            JobStatus.CANCELLED: NotebookResultError,
            JobStatus.DONE: NotebookResultComplete,
            JobStatus.PENDING: NotebookResultPending,
            JobStatus.ERROR: NotebookResultError,
            JobStatus.SUBMITTED: NotebookResultPending,
            JobStatus.TIMEOUT: NotebookResultError,
            JobStatus.DELETED: None,
        }.get(job_status)
        if cls is None:
            return None

        if load_payload and job_status == JobStatus.DONE:

            def read_file(path):
                try:
                    return self.result_data_store.get_last_version(path).read()
                except NoFile:
                    logger.error("Could not find file %s in %s", path, self.result_data_store)
                    return ""

            outputs = {path: read_file(path) for path in result.get("raw_html_resources", {}).get("outputs", [])}
            result["raw_html_resources"]["outputs"] = outputs
            if result.get("generate_pdf_output"):
                pdf_filename = _pdf_filename(result["job_id"])
                result["pdf"] = read_file(pdf_filename)

        if cls == NotebookResultComplete:
            return NotebookResultComplete(
                job_id=result["job_id"],
                job_start_time=result["job_start_time"],
                report_name=result["report_name"],
                status=job_status,
                update_time=result["update_time"],
                job_finish_time=result["job_finish_time"],
                raw_html_resources=result.get("raw_html_resources", {}),
                raw_ipynb_json=result.get("raw_ipynb_json"),
                raw_html=result.get("raw_html"),
                email_html=result.get("email_html"),
                pdf=result.get("pdf", ""),
                overrides=result.get("overrides", {}),
                generate_pdf_output=result.get("generate_pdf_output", True),
                report_title=result.get("report_title", result["report_name"]),
                mailto=result.get("mailto", ""),
                hide_code=result.get("hide_code", False),
                stdout=result.get("stdout", []),
            )
        elif cls == NotebookResultPending:
            return NotebookResultPending(
                job_id=result["job_id"],
                job_start_time=result["job_start_time"],
                report_name=result["report_name"],
                status=job_status,
                update_time=result["update_time"],
                overrides=result.get("overrides", {}),
                generate_pdf_output=result.get("generate_pdf_output", True),
                report_title=result.get("report_title", result["report_name"]),
                mailto=result.get("mailto", ""),
                hide_code=result.get("hide_code", False),
                stdout=result.get("stdout", []),
            )

        elif cls == NotebookResultError:
            return NotebookResultError(
                job_id=result["job_id"],
                job_start_time=result["job_start_time"],
                report_name=result["report_name"],
                status=job_status,
                update_time=result["update_time"],
                error_info=result["error_info"],
                overrides=result.get("overrides", {}),
                generate_pdf_output=result.get("generate_pdf_output", True),
                report_title=result.get("report_title", result["report_name"]),
                mailto=result.get("mailto", ""),
                hide_code=result.get("hide_code", False),
                stdout=result.get("stdout", []),
            )
        else:
            raise ValueError("Could not deserialise {} into result object.".format(result))

    def get_check_result(
        self, job_id: AnyStr
    ) -> Optional[Union[NotebookResultError, NotebookResultComplete, NotebookResultPending]]:
        result = self.library.find_one({"job_id": job_id}, {"_id": 0})
        return self._convert_result(result)

    def get_all_results(
        self,
        since: Optional[datetime.datetime] = None,
        limit: Optional[int] = 100,
        mongo_filter: Optional[Dict] = None,
        load_payload: bool = True,
    ) -> Iterator[Union[NotebookResultComplete, NotebookResultError, NotebookResultPending]]:
        base_filter = {"status": {"$ne": JobStatus.DELETED.value}}
        if mongo_filter:
            base_filter.update(mongo_filter)
        if since:
            base_filter.update({"update_time": {"$gt": since}})
        projection = REMOVE_ID_PROJECTION if load_payload else REMOVE_PAYLOAD_FIELDS_AND_ID_PROJECTION
        results = self.library.find(base_filter, projection).sort("update_time", -1).limit(limit)
        for res in results:
            if res:
                converted_result = self._convert_result(res, load_payload=load_payload)
                if converted_result is not None:
                    yield converted_result

    def get_all_result_keys(self, limit: int = 0, mongo_filter: Optional[Dict] = None) -> List[Tuple[str, str]]:
        keys = []
        base_filter = {"status": {"$ne": JobStatus.DELETED.value}}
        if mongo_filter:
            base_filter.update(mongo_filter)
        results = self.library.aggregate(
            [
                stage
                for stage in (
                    {"$match": base_filter},
                    {"$sort": {"update_time": -1}},
                    {"$limit": limit} if limit else {},
                    {"$project": {"report_name": 1, "job_id": 1}},
                )
                if stage
            ]
        )
        for result in results:
            keys.append((result["report_name"], result["job_id"]))
        return keys

    @staticmethod
    def _mongo_filter(
        report_name: str,
        overrides: Optional[Dict] = None,
        status: Optional[JobStatus] = None,
        as_of: Optional[datetime.datetime] = None,
    ) -> Dict[str, Any]:
        mongo_filter = {"report_name": report_name}
        if overrides is not None:
            # BSON document comparisons are order-specific but we want to compare overrides
            # irrespective of order and so we check subparts independently.
            # See https://stackoverflow.com/questions/14324626/pymongo-or-mongodb-is-treating-two-equal-python-dictionaries-as-different-object
            for k, v in overrides.items():
                mongo_filter["overrides.{}".format(k)] = v
        if status is not None:
            mongo_filter["status"] = status.value
        if as_of is not None:
            mongo_filter["update_time"] = {"$lt": as_of}
        return mongo_filter

    def _get_all_job_ids(
        self,
        report_name: str,
        overrides: Optional[Dict],
        status: Optional[JobStatus] = None,
        as_of: Optional[datetime.datetime] = None,
        limit: int = 0,
    ) -> List[str]:
        mongo_filter = self._mongo_filter(report_name, overrides, status, as_of)
        return [x[1] for x in self.get_all_result_keys(mongo_filter=mongo_filter, limit=limit)]

    def get_all_job_ids_for_name_and_params(self, report_name: str, params: Optional[Dict]) -> List[str]:
        """ Get all the result ids for a given name and parameters, newest first """
        return self._get_all_job_ids(report_name, params)

    def get_latest_job_id_for_name_and_params(
        self, report_name: str, params: Optional[Dict], as_of: Optional[datetime.datetime] = None
    ) -> Optional[str]:
        """ Get the latest result id for a given name and parameters """
        all_job_ids = self._get_all_job_ids(report_name, params, as_of=as_of, limit=1)
        return all_job_ids[0] if all_job_ids else None

    def get_latest_successful_job_id_for_name_and_params(
        self, report_name: str, params: Optional[Dict], as_of: Optional[datetime.datetime] = None
    ) -> Optional[str]:
        """ Get the latest successful job id for a given name and parameters """
        all_job_ids = self._get_all_job_ids(report_name, params, JobStatus.DONE, as_of, limit=1)
        return all_job_ids[0] if all_job_ids else None

    def get_latest_successful_job_ids_for_name_all_params(self, report_name: str) -> List[str]:
        """ Get the latest successful job ids for all parameter variants of a given name"""
        mongo_filter = self._mongo_filter(report_name, status=JobStatus.DONE)
        results = self.library.aggregate(
            [
                {"$match": mongo_filter},
                {"$project": REMOVE_PAYLOAD_FIELDS_PROJECTION},
                {"$sort": {"update_time": -1}},
                {"$group": {"_id": "$overrides", "job_id": {"$first": "$job_id"}}},
            ]
        )

        return [result["job_id"] for result in results]

    def n_all_results(self):
        return self.library.find({"status": {"$ne": JobStatus.DELETED.value}}).count()

    def delete_result(self, job_id: AnyStr) -> None:
        self.update_check_status(job_id, JobStatus.DELETED)


def _pdf_filename(job_id: str) -> str:
    return "{}.pdf".format(job_id)
