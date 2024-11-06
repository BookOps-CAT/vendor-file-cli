import logging
import os
import yaml
from typing import Generator, Optional, Union
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


def configure_sheet() -> Credentials:
    """
    Get or update credentials for google sheets API and save token to file.

    Args:
        None

    Returns:
        google.oauth2.credentials.Credentials: Credentials object for google sheet API.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/accounts.reauth",
    ]
    token_uri = "https://oauth2.googleapis.com/token"

    creds_dict = {
        "token": os.environ["GOOGLE_SHEET_TOKEN"],
        "refresh_token": os.environ["GOOGLE_SHEET_REFRESH_TOKEN"],
        "token_uri": token_uri,
        "client_id": os.environ["GOOGLE_SHEET_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_SHEET_CLIENT_SECRET"],
        "scopes": scopes,
        "universe_domain": "googleapis.com",
        "account": "",
        "expiry": "2024-11-06T15:15:43.146164Z",
    }
    flow_dict = {
        "installed": {
            "client_id": os.environ["GOOGLE_SHEET_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_SHEET_CLIENT_SECRET"],
            "project_id": "marc-record-validator",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": token_uri,
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost"],
        }
    }

    creds = Credentials.from_authorized_user_info(creds_dict)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            logger.debug(
                "Token for Google Sheet API not found. Running credential config flow."
            )
            flow = InstalledAppFlow.from_client_config(flow_dict, scopes)
            creds = flow.run_local_server()
    return creds


def connect(name: str) -> Client:
    """
    Create and return a `Client` object for the specified server using
    credentials stored in env vars.

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
    """Create a dictionary to configure logger."""
    loggly_token = os.environ.get("LOGGLY_TOKEN")
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "basic": {
                "format": "%(app)s-%(asctime)s-%(filename)s-%(lineno)d-%(levelname)s-%(message)s",  # noqa: E501
                "defaults": {"app": "vendor_file_cli"},
            },
            "json": {
                "format": '{"app": "vendor_file_cli", "ascitime": "%(asctime)s", "fileName": "%(name)s", "lineno":"%(lineno)d", "levelname": "%(levelname)s", "message": "%(message)s"}',  # noqa: E501
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
                "propagate": False,
            },
            "vendor_file_cli": {
                "handlers": ["stream", "file", "loggly"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
    }


def get_control_number(record: Record) -> str:
    """Get control number from MARC record to add to validation output."""
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


def get_vendor_list() -> list[str]:
    """
    Read environment variables and return a list of vendors whose
    credentials have been loaded.

    Returns:
        list of vendors (eg. EASTVIEW, LEILA) whose credentials have been loaded.
    """
    try:
        hosts = [i for i in os.environ.keys() if i.endswith("_HOST")]
        vendors = [i.split("_HOST")[0] for i in hosts if "NSDROP" not in i]
        if vendors == []:
            raise ValueError("No vendors found in environment variables.")
        return vendors
    except ValueError as e:
        logger.error(str(e))
        raise e


def load_creds(config_path: Optional[str] = None) -> None:
    """
    Read yaml file with credentials and set as environment variables.

    Args:
        config_path: Path to .yaml file with credentials.

    """
    try:
        if config_path is None and os.environ.get("USERPROFILE") is not None:
            config_path = os.path.join(
                os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml"
            )
        if config_path is None or not os.path.exists(config_path):
            raise ValueError("Vendor credentials file not found.")
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
            if config is None:
                raise ValueError("No credentials found in config file.")
            for k, v in config.items():
                os.environ[k] = str(v)
            vendor_list = get_vendor_list()
            for vendor in vendor_list:
                os.environ[f"{vendor}_DST"] = f"NSDROP/vendor_records/{vendor.lower()}"
    except ValueError as e:
        logger.error(str(e))
        raise e


def read_marc_file_stream(file_obj: File) -> Generator[Record, None, None]:
    """Read the records contained within filestream of File object using pymarc"""
    fh = file_obj.file_stream.getvalue()
    reader = MARCReader(fh)
    for record in reader:
        yield record


def write_data_to_sheet(values: dict) -> Union[dict, None]:
    """
    Write output of validation to google sheet.

    Args:
        values: dictionary containing validation output for a file.

    Returns:
        dictionary containing response from google sheet API.
    """
    vendor_code = values["vendor_code"][0]
    creds = configure_sheet()
    logger.debug("Google sheet API credentials configured.")
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
