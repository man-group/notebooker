import datetime
from typing import Optional

from tqdm import tqdm
import logging

from notebooker.serialization.serialization import get_serializer_from_cls
from notebooker.settings import BaseConfig

logger = logging.getLogger(__name__)


def delete_old_reports(config: BaseConfig, days_cutoff: int, report_name: Optional[str], dry_run: bool = True) -> None:
    """
    Delete notebooker reports older than specified days.

    Args:
        config: The configuration which will point to the serializer class and config.
        days_cutoff: Delete reports older than this many days
        report_name: Optionally specify which report_name we should be removing old reports for.
        dry_run: If True, only show what would be deleted without actually deleting
    """
    serializer = get_serializer_from_cls(config.SERIALIZER_CLS, **config.SERIALIZER_CONFIG)
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_cutoff)

    # Find reports to delete
    to_delete = serializer.get_job_ids_older_than(cutoff_date, report_name=report_name)

    num_reports = len(to_delete)

    if num_reports == 0:
        logger.info(f"No reports found older than {days_cutoff} days")
        return

    logger.info(f"Found {num_reports} reports older than {days_cutoff} days")

    # Delete reports
    logger.info("Starting deletion process...")
    for report in tqdm(to_delete, desc="Deleting reports"):
        try:
            removed = serializer.delete_result(report, dry_run=dry_run)
            logger.info(
                f"{'Would have deleted' if dry_run else 'Deleted'}: "
                f"Title={removed['deleted_result_document']['report_title']}, "
                f"GridFS files={removed['gridfs_filenames']}"
            )
        except Exception as e:
            logger.error(f"Failed to delete report {report}: {str(e)}")

    logger.info(f"{'Would have' if dry_run else 'Successfully'} removed {num_reports} reports")
