"""This module contains functions to be used to configure the CLI and load
credentials."""

import logging
import datetime
import os
from typing import List
import yaml
from file_retriever.connect import Client

logger = logging.getLogger("file_retriever")


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
    vendors: List[str], days: int = 0, hours: int = 0, minutes: int = 0
) -> None:
    """
    Retrieve files from remote server for vendors in `vendor_list`. Forms timedelta
    object from `days`, `hours`, and `minutes` and creates list of files created within
    that time delta. If days, hours, and minutes args are not provided, all files that
    are in the vendor's remote directory will be included in the list. Compares that
    list of files to the list of files in the vendor's NSDROP directory only copies
    the files that are not already present in the NSDROP directory.

    Args:
        vendors: list of vendor names
        days: number of days to retrieve files from (default 0)
        hours: number of hours to retrieve files from (default 0)
        minutes: number of minutes to retrieve files from (default 0)

    Returns:
        None

    """
    nsdrop_client = connect("nsdrop")
    timedelta = datetime.timedelta(days=days, hours=hours, minutes=minutes)

    for vendor in vendors:
        vendor_src_dir = os.environ[f"{vendor.upper()}_SRC"]
        vendor_dst_dir = os.environ[f"{vendor.upper()}_DST"]
        with connect(vendor) as client:
            file_list = client.list_file_info(
                time_delta=timedelta,
                remote_dir=vendor_src_dir,
            )
            files_to_add = nsdrop_client.check_file_list(
                files=file_list, dir=vendor_dst_dir, remote=True
            )
            if len(files_to_add) == 0:
                logger.debug(
                    f"({vendor.upper()}) NSDROP directory is already up to date"
                )
                continue
            logger.debug(f"Writing {len(files_to_add)} files to NSDROP directory")
            for file in files_to_add:
                fetched_file = client.get_file(file=file, remote_dir=vendor_src_dir)
                nsdrop_client.put_file(
                    file=fetched_file,
                    dir=vendor_dst_dir,
                    remote=True,
                    check=True,
                )
    nsdrop_client.close()


def load_vendor_creds(config_path: str) -> List[str]:
    """
    Read config file with credentials and set creds as environment variables.
    Returns a list of vendors whose FTP/SFTP credentials are stored in the
    config file and have been added to env vars. NSDROP is excluded from this list.

    Args:
        config_path (str): Path to the yaml file with credendtials.

    Returns:
        list of names of servers (eg. EASTVIEW, LEILA) whose credentials are
        stored in the config file and have been added to env vars
    """
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
        if config is None:
            raise ValueError("No credentials found in config file.")
        vendor_list = [
            i.split("_HOST")[0]
            for i in config.keys()
            if i.endswith("_HOST") and "NSDROP" not in i
        ]
        for k, v in config.items():
            os.environ[k] = v
        for vendor in vendor_list:
            os.environ[f"{vendor}_DST"] = f"NSDROP/vendor_records/{vendor.lower()}"
        return vendor_list
