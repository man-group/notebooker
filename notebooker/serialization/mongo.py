import datetime
import json
from collections import defaultdict
from logging import getLogger
from typing import Any, AnyStr, Dict, List, Optional, Tuple, Union, Iterator

import click
import gridfs
import pymongo
from abc import ABC
from gridfs import NoFile

from notebooker.constants import JobStatus, NotebookResultComplete, NotebookResultError, NotebookResultPending

logger = getLogger(__name__)
REMOVE_ID_PROJECTION = {"_id": 0}
REMOVE_PAYLOAD_FIELDS_PROJECTION = {"raw_html_resources": 0, "stdout": 0}
REMOVE_PAYLOAD_FIELDS_AND_ID_PROJECTION = dict(REMOVE_PAYLOAD_FIELDS_PROJECTION, **REMOVE_ID_PROJECTION)


def _add_deleted_status_to_filter(base_filter):
    if "status" in base_filter:
        base_filter["status"].update({"$ne": JobStatus.DELETED.value})
    else:
        base_filter["status"] = {"$ne": JobStatus.DELETED.value}
    return base_filter


def ignore_missing_files(f):
    def _ignore_missing_files(path, *args, **kwargs):
        try:
            return f(path, *args, **kwargs)
        except NoFile:
            logger.error("Could not find file %s", path)
            return ""

    return _ignore_missing_files


@ignore_missing_files
def read_file(result_data_store, path, is_json=False):
    r = result_data_store.get_last_version(path).read()
    try:
        return "" if not r else json.loads(r) if is_json else r.decode("utf8")
    except UnicodeDecodeError:
        return r


@ignore_missing_files
def read_bytes_file(result_data_store, path):
    return result_data_store.get_last_version(path).read()


def load_files_from_gridfs(result_data_store: gridfs.GridFS, result: Dict, do_read=True) -> List[str]:
    gridfs_filenames = []
    all_html_output_paths = result.get("raw_html_resources", {}).get("outputs", [])
    gridfs_filenames.extend(all_html_output_paths)
    if do_read:
        outputs = {path: read_file(result_data_store, path) for path in all_html_output_paths}
        result["raw_html_resources"]["outputs"] = outputs
    if result.get("generate_pdf_output"):
        pdf_filename = _pdf_filename(result["job_id"])
        if do_read:
            result["pdf"] = read_bytes_file(result_data_store, pdf_filename)
        gridfs_filenames.append(pdf_filename)
    if not result.get("raw_ipynb_json"):
        json_filename = _raw_json_filename(result["job_id"])
        if do_read:
            result["raw_ipynb_json"] = read_file(result_data_store, json_filename, is_json=True)
        gridfs_filenames.append(json_filename)
    if not result.get("raw_html"):
        html_filename = _raw_html_filename(result["job_id"])
        if do_read:
            result["raw_html"] = read_file(result_data_store, html_filename)
        gridfs_filenames.append(html_filename)
    if not result.get("email_html"):
        email_filename = _raw_email_html_filename(result["job_id"])
        result["email_html"] = read_file(result_data_store, email_filename)
        gridfs_filenames.append(email_filename)
    if result.get("raw_html_resources") and not result.get("raw_html_resources", {}).get("inlining"):
        css_inlining_filename = _css_inlining_filename(result["job_id"])
        if do_read:
            result["raw_html_resources"]["inlining"] = read_file(result_data_store, css_inlining_filename, is_json=True)
        gridfs_filenames.append(css_inlining_filename)
    return gridfs_filenames


class MongoResultSerializer(ABC):
    instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls.instance, cls):
            cls.instance = object.__new__(cls)
        return cls.instance

    # This class is the interface between Mongo and the rest of the application
    def __init__(self, database_name="notebooker", mongo_host="localhost", result_collection_name="NOTEBOOK_OUTPUT"):
        self.database_name = database_name
        self.mongo_host = mongo_host
        self.result_collection_name = result_collection_name

        mongo_database = self.get_mongo_database()
        self.library = mongo_database[result_collection_name]
        self.result_data_store = gridfs.GridFS(mongo_database, "notebook_data")

    def __init_subclass__(cls, cli_options: click.Command = None, **kwargs):
        if cli_options is None:
            raise ValueError(
                "A MongoResultSerializer has been declared without cli_options. "
                "Please add them like so: `class MySerializer(cli_options=cli_opts)`."
            )
        cls.cli_options = cli_options
        super().__init_subclass__(**kwargs)

    def enable_sharding(self):
        conn = self.get_mongo_connection()
        try:
            conn.admin.command("enableSharding", self.database_name)
            conn.admin.command(
                {"shardCollection": f"{self.database_name}.notebook_data.chunks", "key": {"files_id": 1, "n": 1}}
            )
            logger.info(f"Successfully sharded GridFS collection for {self.database_name}")
        except pymongo.errors.OperationFailure:
            logger.error(f"Could not shard {self.database_name}. Continuing.")

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

    def get_mongo_connection(self):
        raise NotImplementedError()

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

    def update_stdout(self, job_id, new_lines, replace=False):
        if replace:
            result = self.library.find_one_and_update({"job_id": job_id}, {"$set": {"stdout": new_lines}})
        else:
            result = self.library.find_one_and_update({"job_id": job_id}, {"$push": {"stdout": {"$each": new_lines}}})

        return result

    def update_check_status(self, job_id: str, status: JobStatus, **extra):
        if status == JobStatus.DONE:
            raise ValueError(
                "update_check_status() should not be called with a completed job; use save_check_result() instead."
            )
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
                if k == "error_info" and v:
                    self.result_data_store.put(v, filename=_error_info_filename(job_id), encoding="utf-8")
                else:
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
        error_mailto: str = "",
        generate_pdf_output: bool = True,
        hide_code: bool = False,
        scheduler_job_id: Optional[str] = None,
        is_slideshow: bool = False,
        email_subject: Optional[str] = None,
        mailfrom: Optional[str] = None,
        category: Optional[str] = None,
    ) -> None:
        """Call this when we are just starting a check. Saves a "pending" job into storage."""
        job_start_time = job_start_time or datetime.datetime.now()
        report_title = report_title or report_name
        pending_result = NotebookResultPending(
            job_id=job_id,
            status=status,
            report_title=report_title,
            job_start_time=job_start_time,
            report_name=report_name,
            mailto=mailto,
            error_mailto=error_mailto,
            email_subject=email_subject,
            generate_pdf_output=generate_pdf_output,
            overrides=overrides or {},
            hide_code=hide_code,
            scheduler_job_id=scheduler_job_id,
            is_slideshow=is_slideshow,
            mailfrom=mailfrom,
            category=category,
        )
        self._save_to_db(pending_result)

    def save_check_result(self, notebook_result: Union[NotebookResultComplete, NotebookResultError]) -> None:
        # Save to gridfs
        for filelike_attribute, filename_func in [
            ("pdf", _pdf_filename),
            ("raw_html", _raw_html_filename),
            ("email_html", _raw_email_html_filename),
            ("error_info", _error_info_filename),
        ]:
            if getattr(notebook_result, filelike_attribute, None):
                self.result_data_store.put(
                    getattr(notebook_result, filelike_attribute),
                    filename=filename_func(notebook_result.job_id),
                    encoding="utf-8",
                )
        for json_attribute, filename_func in [("raw_ipynb_json", _raw_json_filename)]:
            if getattr(notebook_result, json_attribute, None):
                self.result_data_store.put(
                    json.dumps(getattr(notebook_result, json_attribute)),
                    filename=filename_func(notebook_result.job_id),
                    encoding="utf-8",
                )
        if isinstance(notebook_result, NotebookResultComplete):
            if notebook_result.raw_html_resources:
                if "outputs" in notebook_result.raw_html_resources:
                    for filename, binary_data in notebook_result.raw_html_resources["outputs"].items():  # type: ignore
                        self.result_data_store.put(binary_data, filename=filename, encoding="utf-8")
                if "inlining" in notebook_result.raw_html_resources:
                    self.result_data_store.put(
                        json.dumps(notebook_result.raw_html_resources["inlining"]),
                        filename=_css_inlining_filename(notebook_result.job_id),
                        encoding="utf-8",
                    )

        # Save to mongo
        logger.info("Saving {}".format(notebook_result.job_id))
        self._save_to_db(notebook_result)

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

        if not load_payload:
            result.pop("stdout", None)

        if cls == NotebookResultComplete:
            if load_payload:
                load_files_from_gridfs(self.result_data_store, result, do_read=True)
            else:
                result.pop("raw_html", None)
                result.pop("raw_ipynb_json", None)
                result.pop("pdf", None)
                result.pop("email_html", None)
                result.pop("raw_html_resources", None)
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
                mailfrom=result.get("mailfrom", ""),
                error_mailto=result.get("error_mailto", ""),
                hide_code=result.get("hide_code", False),
                stdout=result.get("stdout", []),
                scheduler_job_id=result.get("scheduler_job_id", None),
                is_slideshow=result.get("is_slideshow", False),
                email_subject=result.get("email_subject", None),
                category=result.get("category", None),
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
                mailfrom=result.get("mailfrom", ""),
                error_mailto=result.get("error_mailto", ""),
                email_subject=result.get("email_subject", ""),
                hide_code=result.get("hide_code", False),
                stdout=result.get("stdout", []),
                scheduler_job_id=result.get("scheduler_job_id", None),
                is_slideshow=result.get("is_slideshow", False),
                category=result.get("category", None),
            )

        elif cls == NotebookResultError:
            if load_payload:
                if not result.get("error_info"):
                    result["error_info"] = read_file(self.result_data_store, _error_info_filename(result["job_id"]))
            else:
                result.pop("error_info", None)
            return NotebookResultError(
                job_id=result["job_id"],
                job_start_time=result["job_start_time"],
                report_name=result["report_name"],
                status=job_status,
                update_time=result["update_time"],
                error_info=result.get("error_info", ""),
                overrides=result.get("overrides", {}),
                generate_pdf_output=result.get("generate_pdf_output", True),
                report_title=result.get("report_title", result["report_name"]),
                mailto=result.get("mailto", ""),
                mailfrom=result.get("mailfrom", ""),
                error_mailto=result.get("error_mailto", ""),
                email_subject=result.get("email_subject", ""),
                hide_code=result.get("hide_code", False),
                stdout=result.get("stdout", []),
                scheduler_job_id=result.get("scheduler_job_id", False),
                is_slideshow=result.get("is_slideshow", False),
                category=result.get("category", None),
            )
        else:
            raise ValueError("Could not deserialise {} into result object.".format(result))

    def _get_raw_check_result(self, job_id: str):
        return self.library.find_one({"job_id": job_id}, {"_id": 0})

    def get_check_result(
        self, job_id: AnyStr, load_payload: bool = True
    ) -> Optional[Union[NotebookResultError, NotebookResultComplete, NotebookResultPending]]:
        result = self._get_raw_check_result(job_id)
        return self._convert_result(result, load_payload=load_payload)

    def _get_raw_results(self, base_filter, projection, limit):
        base_filter = _add_deleted_status_to_filter(base_filter)
        return self.library.find(base_filter, projection).sort("update_time", -1).limit(limit)

    def _get_result_count(self, base_filter):
        base_filter = _add_deleted_status_to_filter(base_filter)
        try:
            return self.library.count_documents(base_filter)
        except (TypeError, AttributeError):
            # pymongo<3.7 compat
            return self.library.count(base_filter)

    def get_count_and_latest_time_per_report(self, subfolder: Optional[str]):
        base_filer = {} if not subfolder else {"report_name": {"$regex": subfolder + ".*"}}
        return self.fetch_reports(base_filer)

    def get_count_and_latest_time_per_report_per_category(self, category: Optional[str]):
        base_filer = {} if not category else {"category": category}
        return self.fetch_reports(base_filer)

    def fetch_reports(self, base_filer: Dict[str, Any]):
        reports = list(
            self._get_raw_results(
                base_filter=base_filer,
                projection={"report_name": 1, "job_start_time": 1, "scheduler_job_id": 1, "category": 1, "_id": 0},
                limit=0,
            )
        )
        jobs_by_name = defaultdict(list)
        for r in reports:
            jobs_by_name[r["report_name"]].append(r)
        output = {}
        for report, all_runs in jobs_by_name.items():
            latest_start_time = max(r["job_start_time"] for r in all_runs)
            scheduled_runs = len([x for x in all_runs if x.get("scheduler_job_id")])
            output[report] = {
                "count": len(all_runs),
                "latest_run": latest_start_time,
                "scheduler_runs": scheduled_runs,
                "category": r["category"],
            }
        return output

    def get_all_results(
        self,
        since: Optional[datetime.datetime] = None,
        limit: Optional[int] = 100,
        mongo_filter: Optional[Dict] = None,
        load_payload: bool = True,
    ) -> Iterator[Union[NotebookResultComplete, NotebookResultError, NotebookResultPending]]:
        base_filter = {}
        if mongo_filter:
            base_filter.update(mongo_filter)
        if since:
            base_filter.update({"update_time": {"$gt": since}})
        projection = REMOVE_ID_PROJECTION if load_payload else REMOVE_PAYLOAD_FIELDS_AND_ID_PROJECTION
        results = self._get_raw_results(base_filter, projection, limit)
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
        """Get all the result ids for a given name and parameters, newest first"""
        return self._get_all_job_ids(report_name, params)

    def get_latest_job_id_for_name_and_params(
        self, report_name: str, params: Optional[Dict], as_of: Optional[datetime.datetime] = None
    ) -> Optional[str]:
        """Get the latest result id for a given name and parameters"""
        all_job_ids = self._get_all_job_ids(report_name, params, as_of=as_of, limit=1)
        return all_job_ids[0] if all_job_ids else None

    def get_latest_successful_job_id_for_name_and_params(
        self, report_name: str, params: Optional[Dict], as_of: Optional[datetime.datetime] = None
    ) -> Optional[str]:
        """Get the latest successful job id for a given name and parameters"""
        all_job_ids = self._get_all_job_ids(report_name, params, JobStatus.DONE, as_of, limit=1)
        return all_job_ids[0] if all_job_ids else None

    def get_latest_successful_job_ids_for_name_all_params(self, report_name: str) -> List[str]:
        """Get the latest successful job ids for all parameter variants of a given name"""
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

    def n_all_results_for_report_name(self, report_name: str) -> int:
        return self._get_result_count({"report_name": report_name})

    def delete_result(self, job_id: AnyStr) -> Dict[str, Any]:
        result = self._get_raw_check_result(job_id)
        status = JobStatus.from_string(result["status"])
        gridfs_filenames = load_files_from_gridfs(self.result_data_store, result, do_read=False)
        if status in (JobStatus.ERROR, JobStatus.TIMEOUT, JobStatus.CANCELLED):
            gridfs_filenames.append(_error_info_filename(job_id))
        self.update_check_status(job_id, JobStatus.DELETED)
        for filename in gridfs_filenames:
            logger.info(f"Deleting {filename}")
            for grid_out in self.result_data_store.find({"filename": filename}):
                self.result_data_store.delete(grid_out._id)
        return {"deleted_result_document": result, "gridfs_filenames": gridfs_filenames}


def _pdf_filename(job_id: str) -> str:
    return f"{job_id}.pdf"


def _raw_json_filename(job_id: str) -> str:
    return f"{job_id}.ipynb.json"


def _raw_html_filename(job_id: str) -> str:
    return f"{job_id}.rawhtml"


def _raw_email_html_filename(job_id: str) -> str:
    return f"{job_id}.email.rawhtml"


def _css_inlining_filename(job_id: str) -> str:
    return f"{job_id}.inline.css"


def _error_info_filename(job_id: str) -> str:
    return f"{job_id}.errorinfo"
