from vendor_file_cli.commands import (
    get_vendor_files,
    validate_files,
)
from vendor_file_cli.validator import get_single_file
from vendor_file_cli.utils import connect


def test_get_vendor_files(mock_Client, caplog):
    get_vendor_files(vendors=["leila"], days=300)
    assert "(NSDROP) Connecting to " in caplog.text
    assert "(LEILA) Connecting to " in caplog.text
    assert "(LEILA) 1 file(s) on LEILA server to copy to NSDROP" in caplog.text
    assert "(NSDROP) Writing foo.mrc to `NSDROP/vendor_records/leila`" in caplog.text
    assert "(NSDROP) 1 file(s) copied to `NSDROP/vendor_records/leila`" in caplog.text
    assert "(LEILA) Client session closed" in caplog.text
    assert "(NSDROP) Client session closed" in caplog.text


def test_get_vendor_files_no_files(mock_Client, caplog):
    get_vendor_files(vendors=["eastview"], days=1, hours=1)
    assert "(NSDROP) Connecting to ftp.nsdrop.com via SFTP client" in caplog.text
    assert "(EASTVIEW) Connecting to ftp.eastview.com via SFTP client" in caplog.text
    assert "(EASTVIEW) 0 file(s) on EASTVIEW server to copy to NSDROP" in caplog.text
    assert "(EASTVIEW) Client session closed" in caplog.text
    assert "(NSDROP) Client session closed" in caplog.text


def test_get_single_file_no_validation(mock_Client, stub_file_info, caplog):
    vendor_client = connect("midwest_nypl")
    nsdrop_client = connect("nsdrop")
    get_single_file(
        vendor="midwest_nypl",
        file=stub_file_info,
        vendor_client=vendor_client,
        nsdrop_client=nsdrop_client,
    )
    assert (
        "(MIDWEST_NYPL) Connecting to ftp.midwest_nypl.com via FTP client"
        in caplog.text
    )
    assert "(NSDROP) Connecting to ftp.nsdrop.com via SFTP client" in caplog.text
    assert "(NSDROP) Validating bar file: foo.mrc" not in caplog.text
    assert (
        "(NSDROP) Writing foo.mrc to `NSDROP/vendor_records/midwest_nypl`"
        in caplog.text
    )


def test_get_single_file_with_validation(mock_Client, stub_file_info, caplog):
    vendor_client = connect("eastview")
    nsdrop_client = connect("nsdrop")
    get_single_file(
        vendor="eastview",
        file=stub_file_info,
        vendor_client=vendor_client,
        nsdrop_client=nsdrop_client,
    )
    assert "(EASTVIEW) Connecting to ftp.eastview.com via SFTP client" in caplog.text
    assert "(NSDROP) Connecting to ftp.nsdrop.com via SFTP client" in caplog.text
    assert "(NSDROP) Validating eastview file: foo.mrc" in caplog.text
    assert "(NSDROP) Writing foo.mrc to `NSDROP/vendor_records/eastview`" in caplog.text


def test_validate_files(mock_Client, caplog):
    validate_files(vendor="eastview", files=None)
    assert "(NSDROP) Connecting to " in caplog.text
    assert "(NSDROP) Validating eastview file: bar.mrc" in caplog.text


def test_validate_files_with_list(mock_Client, caplog):
    validate_files(vendor="eastview", files=["foo.mrc"])
    assert "(NSDROP) Connecting to " in caplog.text
    assert "(NSDROP) Validating eastview file: foo.mrc" in caplog.text
