from collections import defaultdict
import datetime
import logging
import os
from typing import Any
from pydantic import ValidationError
from pymarc import Record
from file_retriever import Client, File, FileInfo
from record_validator.marc_models import RecordModel
from record_validator.marc_errors import MarcValidationError
from vendor_file_cli.utils import (
    read_marc_file_stream,
    get_control_number,
    write_data_to_sheet,
)

logger = logging.getLogger(__name__)


def get_single_file(
    vendor: str,
    file: FileInfo,
    vendor_client: Client,
    nsdrop_client: Client,
    test: bool,
) -> File:
    """
    Get a file from a vendor server and copy it to the vendor's NSDROP directory.
    Validates the file if the vendor is EASTVIEW, LEILA, or AMALIVRE_SASB.

    Args:
        vendor: name of vendor
        file: `FileInfo` object representing the file to retrieve
        vendor_client: `Client` object for the vendor server
        nsdrop_client: `Client` object for the NSDROP server

    Returns:
        None

    """
    if vendor.lower() == "bakertaylor_bpl" and file.file_name.startswith(
        ("ADD", "NEW")
    ):
        remote_dir = ""
    else:
        remote_dir = os.environ[f"{vendor.upper()}_SRC"]
    nsdrop_dir = os.environ[f"{vendor.upper()}_DST"]
    fetched_file = vendor_client.get_file(file=file, remote_dir=remote_dir)
    nsdrop_client.put_file(file=fetched_file, dir=nsdrop_dir, remote=True, check=True)
    if vendor.upper() in ["EASTVIEW", "LEILA", "AMALIVRE_SASB"]:
        logger.debug(
            f"({nsdrop_client.name}) Validating {vendor} file: {fetched_file.file_name}"
        )
        validate_file(file_obj=fetched_file, vendor=vendor, test=test)
    return fetched_file


def get_vendor_file_list(
    vendor: str,
    timedelta: datetime.timedelta,
    nsdrop_client: Client,
    vendor_client: Client,
) -> list[FileInfo]:
    """
    Create list of files to retrieve from vendor server. Compares list of files
    on vendor server to list of files in vendor's directory on NSDROP. Only
    includes files that are not already present in the NSDROP directory. The
    list of files is filtered based on the timedelta provided.

    If the vendor is BAKERTAYLOR_NYPL, the root directory of the is also checked
    for files that are not in the NSDROP directory. This is because the
    BAKERTAYLOR_NYPL server has multiple directories that contain files that
    need to be copied to NSDROP.

    If the vendor is MIDWEST_NYPL, the directories are compared using just
    the file names and then a list of FileInfo objects is created from the
    list of file names. This is due to the fact that there are nearly 10k files
    on the MIDWEST_NYPL server.

    Args:

        vendor: name of vendor
        timedelta: timedelta object representing the time period to retrieve files from
        nsdrop_client: `Client` object for the NSDROP server
        vendor_client: `Client` object for the vendor server

    Returns:
        list of `FileInfo` objects representing files to retrieve from the vendor server
    """
    today = datetime.datetime.now(tz=datetime.timezone.utc)
    nsdrop_files = nsdrop_client.list_files(os.environ[f"{vendor}_DST"])
    vendor_files = vendor_client.list_file_info(os.environ[f"{vendor}_SRC"])

    if vendor.lower() == "bakertaylor_bpl":
        vendor_files.extend(vendor_client.list_file_info(""))

    return [
        i
        for i in vendor_files
        if i.file_name not in nsdrop_files
        and datetime.datetime.fromtimestamp(i.file_mtime, tz=datetime.timezone.utc)
        >= today - timedelta
    ]


def validate_file(file_obj: File, vendor: str, test: bool) -> dict:
    """
    Validate a file of MARC records and output to google sheet.

    Args:
        file_obj: `File` object representing the file to validate.
        vendor: name of vendor to validate file for.
        write: whether to write the validation results to the google sheet.

    Returns:
        dictionary containing validation output for the file.

    """
    if "AMALIVRE" in vendor.upper():
        vendor_code = "AUXAM"
    elif "EASTVIEW" in vendor.upper():
        vendor_code = "EVP"
    elif "LEILA" in vendor.upper():
        vendor_code = "LEILA"
    else:
        vendor_code = vendor.upper()
    record_count = len([i for i in read_marc_file_stream(file_obj)])
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
    write_data_to_sheet(out_dict, test=test)
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
    for field in [
        i
        for i in [
            "error_count",
            "missing_field_count",
            "extra_field_count",
            "invalid_field_count",
            "missing_fields",
            "extra_fields",
            "invalid_fields",
            "order_item_mismatches",
        ]
        if i not in out
    ]:
        out[field] = ""
    return out
