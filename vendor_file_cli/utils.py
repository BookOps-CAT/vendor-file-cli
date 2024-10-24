import logging
import logging.config
import os
import yaml
from typing import Generator
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
import pandas as pd
from pymarc import MARCReader, Record
from file_retriever.connect import Client
from file_retriever.file import File

logger = logging.getLogger(__name__)


def configure_logger(logger_dict: dict) -> None:
    logging.config.dictConfig(logger_dict)
    loggers = [i for i in logger_dict["loggers"].keys()]
    for logger in loggers:
        logging.getLogger(f"{logger}")


def configure_sheet() -> Credentials:
    """
    Get or update credentials for google sheets API and save token to file.

    Args:
        None

    Returns:
        google.oauth2.credentials.Credentials: Credentials object for google sheet API.
    """
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    cred_path = os.path.join(
        os.environ["USERPROFILE"], ".cred/.google/desktop-app.json"
    )
    token_path = os.path.join(os.environ["USERPROFILE"], ".cred/.google/token.json")

    creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, scopes)
            creds = flow.run_local_server()
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return creds


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


def create_logger_dict() -> dict:
    loggly_token = os.environ.get("LOGGLY_TOKEN")
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "basic": {
                "format": "%(app_name)s-%(asctime)s-%(name)s-%(lineno)d-%(levelname)s-%(message)s",  # noqa: E501
                "defaults": {"app_name": "vendor_file_cli"},
            },
            "json": {
                "format": '{"app_name": "%(app_name)s", "asctime": "%(asctime)s", "name": "%(name)s", "lineno":"%(lineno)d", "levelname": "%(levelname)s", "message": "%(message)s"}'  # noqa: E501
            },
        },
        "handlers": {
            "stream": {
                "class": "logging.StreamHandler",
                "formatter": "basic",
                "level": "DEBUG",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "basic",
                "level": "DEBUG",
                "filename": "vendor_file_cli.log",
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
            },
            "loggly": {
                "class": "loggly.handlers.HTTPSHandler",
                "formatter": "json",
                "level": "INFO",
                "url": f"https://logs-01.loggly.com/inputs/{loggly_token}/tag/python",
            },
        },
        "loggers": {
            "file_retriever": {
                "handlers": ["stream", "file", "loggly"],
                "level": "DEBUG",
                "propagate": True,
            },
            "file_retriever.vendor_file_cli": {
                "handlers": ["stream", "file", "loggly"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
    }


def get_control_number(record: Record) -> str:
    """Get control number from MARC record to output to google sheet."""
    field = record.get("001", None)
    if field is not None:
        control_number = field.data
        if control_number is not None:
            return control_number
    field_subfield_pairs = [
        ("035", "a"),
        ("020", "a"),
        ("010", "a"),
        ("022", "a"),
        ("024", "a"),
        ("852", "h"),
    ]
    for f, s in field_subfield_pairs:
        while record.get(f, None) is not None:
            field = record.get(f, None)
            if field is not None:
                subfield = field.get(s)
                if subfield is not None:
                    return subfield
    return "None"


def load_vendor_creds(config_path: str) -> list[str]:
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
            os.environ[str(k)] = str(v)
        for vendor in vendor_list:
            os.environ[f"{vendor}_DST"] = f"NSDROP/vendor_records/{vendor.lower()}"
        return vendor_list


def read_marc_file_stream(file_obj: File) -> Generator[Record, None, None]:
    """Read the filestream within a File object using pymarc"""
    fh = file_obj.file_stream.getvalue()
    reader = MARCReader(fh)
    for record in reader:
        yield record


def write_data_to_sheet(values: dict) -> dict | None:
    """"""
    vendor_code = values["vendor_code"][0]
    creds = configure_sheet()

    df = pd.DataFrame(
        values,
        columns=[
            "validation_date",
            "file_name",
            "vendor_code",
            "record_number",
            "control_number",
            "valid",
            "error_count",
            "missing_field_count",
            "missing_fields",
            "extra_field_count",
            "extra_fields",
            "invalid_field_count",
            "invalid_fields",
            "order_item_mismatches",
        ],
    )
    df.fillna("", inplace=True)

    body = {
        "majorDimension": "ROWS",
        "range": f"{vendor_code.upper()}!A1:O10000",
        "values": df.values.tolist(),
    }
    try:
        service = build("sheets", "v4", credentials=creds)
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId="1ZYuhMIE1WiduV98Pdzzw7RwZ08O-sJo7HJihWVgSOhQ",
                range=f"{vendor_code.upper()}!A1:O10000",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
                includeValuesInResponse=True,
            )
            .execute()
        )
        return result
    except (HttpError, TimeoutError) as e:
        logger.error(f"Error occurred while sending data to google sheet: {e}")
        return None
