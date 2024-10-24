"""This module contains functions to use to configure the CLI, logger, and env vars."""

import logging
import logging.handlers
import datetime
import os
from vendor_file_cli.validator import (
    validate_file,
    get_single_file,
    get_vendor_file_list,
)
from vendor_file_cli.utils import connect


logger = logging.getLogger(__name__)


def get_vendor_files(
    vendors: list[str],
    days: int = 0,
    hours: int = 0,
) -> None:
    """
    Retrieve files from remote server for vendors in `vendor_list`. Forms timedelta
    object from `days` and `hours` and creates list of files created within
    that time delta. If days and hours args are not provided, all files that
    are in the vendor's remote directory will be included in the list. Compares that
    list of files to the list of files in the vendor's NSDROP directory only copies
    the files that are not already present in the NSDROP directory. Will validate files
    before copying if validate is True.

    Args:
        vendors: list of vendor names
        days: number of days to retrieve files from (default 0)
        hours: number of hours to retrieve files from (default 0)

    Returns:
        None

    """
    for vendor in vendors:
        with connect("nsdrop") as nsdrop_client:
            with connect(vendor) as vendor_client:
                files = get_vendor_file_list(
                    vendor=vendor,
                    timedelta=datetime.timedelta(days=days, hours=hours),
                    nsdrop_client=nsdrop_client,
                    vendor_client=vendor_client,
                )
                for file in files:
                    get_single_file(
                        vendor=vendor,
                        file=file,
                        vendor_client=vendor_client,
                        nsdrop_client=nsdrop_client,
                    )
                if len(files) > 0:
                    logger.info(
                        f"({nsdrop_client.name}) {len(files)} file(s) "
                        f"copied to `{os.environ[f"{vendor.upper()}_DST"]}`"
                    )


def validate_files(vendor: str, files: list | None) -> None:
    """
    Validate files on NSDROP for a speific vendor.

    Args:
        vendor:
            name of vendor
        files:
            list of file names to validate (default None). If None, all
            files in the vendor's directory on NSDROP will be validated.

    Returns:
        None
    """
    file_dir = os.environ[f"{vendor.upper()}_DST"]
    vendor_file_list = []
    with connect("nsdrop") as nsdrop_client:
        if files and files is not None:
            for file in files:
                vendor_file_list.append(
                    nsdrop_client.get_file_info(file_name=file, remote_dir=file_dir)
                )
        else:
            vendor_file_list.extend(nsdrop_client.list_file_info(remote_dir=file_dir))
    for file in vendor_file_list:
        client = connect("nsdrop")
        file_obj = client.get_file(file=file, remote_dir=file_dir)
        logger.debug(f"({client.name}) Validating {vendor} file: {file_obj.file_name}")
        validate_file(file_obj=file_obj, vendor=vendor)
        client.close()
