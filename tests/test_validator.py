import datetime
import pytest
from vendor_file_cli.validator import (
    get_single_file,
    get_vendor_file_list,
    validate_file,
    validate_single_record,
)


@pytest.mark.parametrize("vendor", ["midwest_nypl", "bakertaylor_bpl"])
def test_get_single_file_no_validation(stub_client, stub_file_info, vendor, caplog):
    vendor_client = stub_client(vendor)
    nsdrop_client = stub_client("nsdrop")
    get_single_file(
        vendor=vendor,
        file=stub_file_info,
        vendor_client=vendor_client,
        nsdrop_client=nsdrop_client,
        test=True,
    )
    assert (
        f"({vendor.upper()}) Connecting to ftp.{vendor}.com via FTP client"
        in caplog.text
    )
    assert "(NSDROP) Connecting to ftp.nsdrop.com via SFTP client" in caplog.text
    assert f"(NSDROP) Validating {vendor} file: foo.mrc" not in caplog.text
    assert (
        f"(NSDROP) Writing foo.mrc to `NSDROP/vendor_records/{vendor}`" in caplog.text
    )


def test_get_single_file_with_validation(stub_client, stub_file_info, caplog):
    vendor_client = stub_client("eastview")
    nsdrop_client = stub_client("nsdrop")
    get_single_file(
        vendor="eastview",
        file=stub_file_info,
        vendor_client=vendor_client,
        nsdrop_client=nsdrop_client,
        test=True,
    )
    assert "(EASTVIEW) Connecting to ftp.eastview.com via SFTP client" in caplog.text
    assert "(NSDROP) Connecting to ftp.nsdrop.com via SFTP client" in caplog.text
    assert "(NSDROP) Validating eastview file: foo.mrc" in caplog.text
    assert "(NSDROP) Writing foo.mrc to `NSDROP/vendor_records/eastview`" in caplog.text


def test_get_single_file_bakertaylor_bpl_root(stub_client, stub_file_info, caplog):
    vendor_client = stub_client("bakertaylor_bpl")
    nsdrop_client = stub_client("nsdrop")
    stub_file_info.file_name = "ADDfoo.mrc"
    get_single_file(
        vendor="bakertaylor_bpl",
        file=stub_file_info,
        vendor_client=vendor_client,
        nsdrop_client=nsdrop_client,
        test=True,
    )
    assert (
        "(BAKERTAYLOR_BPL) Connecting to ftp.bakertaylor_bpl.com via FTP client"
        in caplog.text
    )
    assert "(NSDROP) Connecting to ftp.nsdrop.com via SFTP client" in caplog.text
    assert (
        "(NSDROP) Writing ADDfoo.mrc to `NSDROP/vendor_records/bakertaylor_bpl`"
        in caplog.text
    )


@pytest.mark.parametrize("vendor", ["midwest_nypl", "bakertaylor_bpl"])
def test_get_vendor_file_list(stub_client, vendor, caplog):
    file_list = []
    with stub_client("nsdrop") as nsdrop_client:
        with stub_client(vendor) as vendor_client:
            file_list.extend(
                get_vendor_file_list(
                    vendor=vendor,
                    timedelta=datetime.timedelta(days=1),
                    nsdrop_client=nsdrop_client,
                    vendor_client=vendor_client,
                )
            )
    assert len(file_list) == 0
    assert "(NSDROP) Connecting to ftp.nsdrop.com via SFTP client" in caplog.text
    assert (
        f"({vendor.upper()}) Connecting to ftp.{vendor}.com via FTP client"
        in caplog.text
    )
    assert f"({vendor.upper()}) Client session closed" in caplog.text
    assert "(NSDROP) Client session closed" in caplog.text


@pytest.mark.parametrize(
    "vendor, vendor_code",
    [
        ("amalivre_sasb", "AUXAM"),
        ("eastview", "EVP"),
        ("leila", "LEILA"),
        ("midwest_nypl", "MIDWEST_NYPL"),
    ],
)
def test_validate_file(stub_file, vendor, vendor_code, mock_sheet_config):
    out_dict = validate_file(stub_file, vendor, test=True)
    assert sorted([i for i in out_dict.keys()]) == sorted(
        [
            "valid",
            "record_number",
            "control_number",
            "file_name",
            "validation_date",
            "vendor_code",
            "error_count",
            "missing_field_count",
            "missing_fields",
            "extra_field_count",
            "extra_fields",
            "invalid_field_count",
            "invalid_fields",
            "order_item_mismatches",
        ]
    )
    assert out_dict["vendor_code"] == [vendor_code]


def test_validate_single_record(mock_valid_record):
    assert validate_single_record(mock_valid_record) == {
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


def test_validate_single_record_invalid(mock_invalid_record):
    assert validate_single_record(mock_invalid_record) == {
        "valid": False,
        "error_count": 1,
        "missing_field_count": 1,
        "missing_fields": ["960"],
        "extra_field_count": 0,
        "extra_fields": [],
        "invalid_field_count": 0,
        "invalid_fields": [],
        "order_item_mismatches": [],
    }
