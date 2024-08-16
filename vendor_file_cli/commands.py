"""This module contains functions to be used to configure the CLI and load
credentials."""

import datetime
import os
import logging
import logging.config
from typing import List, Optional
import yaml
from file_retriever.connect import Client
from file_retriever.utils import logger_config

logger = logging.getLogger("file_retriever")
config = logger_config()
logging.config.dictConfig(config)


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


def get_recent_files(
    vendors: List[str], days: int = 0, hours: int = 0, minutes: int = 0
) -> None:
    """
    Retrieve files from remote server for vendors in `vendor_list`.
    Creates timedelta object from `days`, `hours`, and `minutes` and retrieves
    files created in the last x days where x is today - timedelta. If days, hours,
    or minutes are not provided, all files will be retrieved from the remote server.

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
        with connect(vendor) as client:
            file_list = [
                i
                for i in client.list_file_info(
                    time_delta=timedelta,
                    remote_dir=os.environ[f"{vendor.upper()}_SRC"],
                )
            ]
            if len(file_list) == 0:
                continue
            for file in file_list:
                fetched_file = client.get_file(
                    file=file, remote_dir=os.environ[f"{vendor.upper()}_SRC"]
                )
                nsdrop_client.put_file(
                    file=fetched_file,
                    dir=os.environ[f"{vendor.upper()}_DST"],
                    remote=True,
                    check=True,
                )


def load_vendor_creds(config_path: str) -> Optional[List[str]]:
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
            return None
        for k, v in config.items():
            os.environ[k] = v
        vendor_list = [
            i.split("_HOST")[0]
            for i in config.keys()
            if i.endswith("_HOST") and i != "NSDROP"
        ]
        return vendor_list
