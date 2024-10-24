from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Any, List, Union
from pydantic import ValidationError
from pymarc import Record
from file_retriever.file import File, FileInfo
from file_retriever.connect import Client
from record_validator.marc_models import RecordModel
from record_validator.marc_errors import MarcValidationError
from vendor_file_cli.utils import (
    read_marc_file_stream,
    get_control_number,
    write_data_to_sheet,
)

logger = logging.getLogger(__name__)


def get_single_file(
    vendor: str, file: FileInfo, vendor_client: Client, nsdrop_client: Client
) -> File:
    """
    Get a file from a vendor server and put it in the NSDROP directory.
    Validates the file if the vendor is EASTVIEW, LEILA, or AMALIVRE_SASB.

    Args:
        vendor: name of vendor
        file: `FileInfo` object representing the file to retrieve
        vendor_client: `Client` object for the vendor server
        nsdrop_client: `Client` object for the NSDROP server

    Returns:
        None

    """
    if (
        file.file_name.startswith("ADD") or file.file_name.startswith("NEW")
    ) and vendor.lower() == "bakertaylor_bpl":
        remote_dir = ""
    else:
        remote_dir = os.environ[f"{vendor.upper()}_SRC"]
    fetched_file = vendor_client.get_file(file=file, remote_dir=remote_dir)
    if vendor.upper() in ["EASTVIEW", "LEILA", "AMALIVRE_SASB"]:
        logger.debug(
            f"({nsdrop_client.name}) Validating {vendor} file: {fetched_file.file_name}"
        )
        out_data = validate_file(file_obj=fetched_file, vendor=vendor)
        write_data_to_sheet(out_data)
    nsdrop_client.put_file(
        file=fetched_file,
        dir=os.environ[f"{vendor.upper()}_DST"],
        remote=True,
        check=True,
    )
    return fetched_file


def get_vendor_file_list(
    vendor: str, timedelta: timedelta, nsdrop_client: Client, vendor_client: Client
) -> list[FileInfo]:
    """"""
    nsdrop_files: Union[List[FileInfo], List[str]]
    vendor_files: Union[List[FileInfo], List[str]]

    today = datetime.now(tz=timezone.utc)
    src_dir = os.environ[f"{vendor.upper()}_SRC"]
    dst_dir = os.environ[f"{vendor.upper()}_DST"]
    if vendor.lower() == "midwest_nypl":
        nsdrop_files = nsdrop_client.list_files(remote_dir=dst_dir)
        vendor_files = vendor_client.list_files(remote_dir=src_dir)
        files_to_check = [
            i
            for i in vendor_files
            if ".mrc" in i
            and i.split("_ALL")[0].endswith("2024")
            and int(i.split("_")[1][3:5]) >= 7
            and i not in nsdrop_files
        ]
        file_data = [
            vendor_client.get_file_info(
                file_name=i, remote_dir=os.environ["MIDWEST_NYPL_SRC"]
            )
            for i in files_to_check
        ]
    else:
        nsdrop_files = nsdrop_client.list_file_info(dst_dir)
        vendor_files = vendor_client.list_file_info(src_dir)
        file_data = [
            i
            for i in vendor_files
            if i.file_name not in [j.file_name for j in nsdrop_files]
        ]
        if vendor.lower() == "bakertaylor_bpl":
            other_files = vendor_client.list_file_info("")
            file_data.extend(
                [
                    i
                    for i in other_files
                    if i.file_name not in [j.file_name for j in nsdrop_files]
                ]
            )
    files_to_get = [
        i
        for i in file_data
        if datetime.fromtimestamp(i.file_mtime, tz=timezone.utc) >= today - timedelta
    ]
    logger.debug(
        f"({vendor_client.name}) {len(files_to_get)} file(s) on "
        f"{vendor_client.name} server to copy to NSDROP"
    )
    return files_to_get


def validate_file(file_obj: File, vendor: str) -> dict:
    """
    Validate a file of MARC records and output to google sheet.

    Args:
        file_obj: `File` object representing the file to validate.
        vendor: name of vendor to validate file for.
        write: whether to write the validation results to the google sheet.

    Returns:
        None

    """
    if "AMALIVRE" in vendor.upper():
        vendor_code = "AUXAM"
    elif "EASTVIEW" in vendor.upper():
        vendor_code = "EVP"
    elif "LEILA" in vendor.upper():
        vendor_code = "LEILA"
    else:
        vendor_code = vendor.upper()
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
                "validation_date": datetime.today().strftime("%Y-%m-%d %I:%M:%S"),
            }
        )
        for k, v in validation_data.items():
            out_dict[k].append(str(v))
        record_n += 1
    return out_dict


def validate_single_record(record: Record) -> dict[str, Any]:
    """
    Validate a single MARC record using the RecordModel. If the record is invalid,
    return a dictionary with the error information. If the record is valid, return
    a dictionary with the validation information.

    Args:
        record: pymarc.Record object representing the record to validate.

    Returns:
        dictionary with validation output.
    """
    out: dict[str, Any]
    try:
        RecordModel(leader=str(record.leader), fields=record.fields)
        out = {"valid": True}
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
