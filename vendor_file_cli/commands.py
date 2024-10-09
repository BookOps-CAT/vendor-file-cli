"""This module contains functions to use to configure the CLI, logger, and env vars."""

import logging
import logging.handlers
import datetime
import os
from file_retriever.connect import Client
from file_retriever.file import FileInfo
from vendor_file_cli.validator import validate_file


logger = logging.getLogger("vendor_file_cli")


def connect(name: str) -> Client:
    """
    Create and return a `Client` object for the specified server
    using credentials stored in env vars.

    Args:
        name: name of server (eg. EASTVIEW, NSDROP)

    Returns:
        a `Client` object for the specified server
    """
    client_name = name.upper()
    return Client(
        name=client_name,
        username=os.environ[f"{client_name}_USER"],
        password=os.environ[f"{client_name}_PASSWORD"],
        host=os.environ[f"{client_name}_HOST"],
        port=os.environ[f"{client_name}_PORT"],
    )


def get_vendor_files(
    vendors: list[str],
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
) -> None:
    """
    Retrieve files from remote server for vendors in `vendor_list`. Forms timedelta
    object from `days`, `hours`, and `minutes` and creates list of files created within
    that time delta. If days, hours, and minutes args are not provided, all files that
    are in the vendor's remote directory will be included in the list. Compares that
    list of files to the list of files in the vendor's NSDROP directory only copies
    the files that are not already present in the NSDROP directory. Will validate files
    before copying if validate is True.

    Args:
        vendors: list of vendor names
        days: number of days to retrieve files from (default 0)
        hours: number of hours to retrieve files from (default 0)
        minutes: number of minutes to retrieve files from (default 0)

    Returns:
        None

    """
    nsdrop = connect("nsdrop")
    timedelta = datetime.timedelta(days=days, hours=hours, minutes=minutes)
    for vendor in vendors:
        with connect(vendor) as client:
            file_list = client.list_file_info(
                time_delta=timedelta,
                remote_dir=os.environ[f"{vendor.upper()}_SRC"],
            )
            files = nsdrop.check_file_list(
                files=file_list, dir=os.environ[f"{vendor.upper()}_DST"], remote=True
            )
            for file in files:
                get_single_file(
                    vendor=vendor,
                    file=file,
                    vendor_client=client,
                    nsdrop_client=nsdrop,
                )
    nsdrop.close()


def get_single_file(
    vendor: str, file: FileInfo, vendor_client: Client, nsdrop_client: Client
) -> None:
    fetched_file = vendor_client.get_file(
        file=file, remote_dir=os.environ[f"{vendor.upper()}_SRC"]
    )
    if vendor.upper() in ["EASTVIEW", "LEILA", "AMALIVRE_SASB"]:
        logger.info(
            f"({nsdrop_client.name}) Validating {vendor} file: {fetched_file.file_name}"
        )
        validate_file(file_obj=fetched_file, vendor=vendor, write=True)
    nsdrop_client.put_file(
        file=fetched_file,
        dir=os.environ[f"{vendor.upper()}_DST"],
        remote=True,
        check=True,
    )


def validate_files(vendor: str, files: list | None) -> None:
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
        logger.info(f"({client.name}) Validating {vendor} file: {file_obj.file_name}")
        validate_file(file_obj=file_obj, vendor=vendor, write=True)
        client.close()
