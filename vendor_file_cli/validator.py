from collections import defaultdict
import datetime
import logging
import os
from typing import Any, Generator
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
from pydantic import ValidationError
from pymarc import MARCReader, Record
from file_retriever.file import File
from record_validator.marc_models import RecordModel
from record_validator.marc_errors import MarcValidationError

logger = logging.getLogger("vendor_file_cli")


def configure_sheet() -> Credentials:
    """
    A function to append data to a google sheet for a specific vendor
    """
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    cred_path = os.path.join(
        os.environ["USERPROFILE"], ".cred/.google/desktop-app.json"
    )
    token_path = os.path.join(os.environ["USERPROFILE"], ".cred/.google/token.json")

    if os.path.exists(token_path):
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


def get_control_number(record: Record) -> str:
    try:
        return str(record["001"].data)
    except KeyError:
        pass
    try:
        return record["035"]["a"]
    except KeyError:
        pass
    try:
        return record["020"]["a"]
    except KeyError:
        pass
    try:
        return record["010"]["a"]
    except KeyError:
        pass
    try:
        return record["022"]["a"]
    except KeyError:
        pass
    try:
        return record["024"]["a"]
    except KeyError:
        pass
    try:
        return record["852"]["h"]
    except KeyError:
        return "None"


def map_vendor_to_code(vendor: str) -> str:
    vendor_map = {
        "EASTVIEW": "EVP",
        "LEILA": "LEILA",
        "AMALIVRE_SASB": "AUXAM",
        "AMALIVRE_LPA": "AUXAM",
        "AMALIVRE_SCHOMBURG": "AUXAM",
        "AMALIVRE_RL": "AUXAM",
    }
    return vendor_map[vendor.upper()]


def read_marc_file_stream(file_obj: File) -> Generator[Record, None, None]:
    """for file on NSDROP as File object"""
    fh = file_obj.file_stream.getvalue()
    reader = MARCReader(fh)
    for record in reader:
        yield record


def send_data_to_sheet(vendor_code: str, values: list, creds: Credentials):
    """
    A function to append data to a google sheet for a specific vendor
    """
    body = {
        "majorDimension": "ROWS",
        "range": f"{vendor_code.upper()}!A1:O10000",
        "values": values,
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


def validate_single_record(record: Record) -> dict[str, Any]:
    try:
        RecordModel(leader=str(record.leader), fields=record.fields)
        out = {
            "valid": True,
            "error_count": "",
            "missing_field_count": "",
            "missing_fields": "",
            "extra_field_count": "",
            "extra_fields": "",
            "invalid_field_count": "",
            "invalid_fields": "",
            "order_item_mismatches": "",
        }
    except ValidationError as e:
        out = {"valid": False}
        marc_errors = MarcValidationError(e.errors())
        out.update(marc_errors.to_dict())
        out.update(
            {
                "missing_field_count": len(marc_errors.missing_fields),
                "invalid_field_count": len(marc_errors.invalid_fields),
                "extra_field_count": len(marc_errors.extra_fields),
            }
        )
    return out


def validate_file(file_obj: File, vendor: str, write: bool) -> None:
    if vendor.upper() in ["EASTVIEW", "LEILA", "AMALIVRE_SASB"]:
        vendor_code = map_vendor_to_code(vendor)
        record_count = len([record for record in read_marc_file_stream(file_obj)])
        reader = read_marc_file_stream(file_obj)
        record_n = 1
        out_dict = defaultdict(list)
        for record in reader:
            validation_data = validate_single_record(record)
            validation_data.update(
                {
                    "record_number": f"{record_n} of {record_count}",
                    "control_number": get_control_number(record),
                    "file_name": file_obj.file_name,
                    "vendor_code": vendor_code,
                    "validation_date": datetime.datetime.today().strftime(
                        "%Y-%m-%d %I:%M:%S"
                    ),
                }
            )
            for k, v in validation_data.items():
                out_dict[k].append(str(v))
            record_n += 1
        df = pd.DataFrame(
            out_dict,
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
        if write is True:
            send_data_to_sheet(
                vendor_code,
                df.values.tolist(),
                configure_sheet(),
            )
