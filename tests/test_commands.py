from vendor_file_cli.commands import get_vendor_files, validate_files


def test_get_vendor_files(mock_Client, caplog):
    get_vendor_files(vendors=["leila"], days=300)
    assert "(NSDROP) Connecting to " in caplog.text
    assert "(LEILA) Connecting to " in caplog.text
    assert "(LEILA) 1 file(s) on LEILA server to copy to NSDROP" in caplog.text
    assert "(NSDROP) Writing foo.mrc to `NSDROP/vendor_records/leila`" in caplog.text
    assert "(NSDROP) 1 file(s) copied to `NSDROP/vendor_records/leila`" in caplog.text
    assert "(LEILA) Client session closed" in caplog.text
    assert "(NSDROP) Client session closed" in caplog.text


def test_get_vendor_files_invalid_creds(mock_Client_auth_error, caplog):
    get_vendor_files(vendors=["leila", "eastview", "midwest_nypl"], days=300)
    assert (
        "file_retriever._clients",
        40,
        "(LEILA) Unable to authenticate with provided credentials: ",
    ) in caplog.record_tuples
    assert "(NSDROP) Connecting to ftp.nsdrop.com via SFTP client" in caplog.text
    assert "(EASTVIEW) Connecting to ftp.eastview.com via SFTP client" in caplog.text
    assert "(EASTVIEW) 1 file(s) on EASTVIEW server to copy to NSDROP" in caplog.text
    assert "(EASTVIEW) Client session closed" in caplog.text
    assert "(NSDROP) Client session closed" in caplog.text


def test_get_vendor_files_no_files(mock_Client, caplog):
    get_vendor_files(vendors=["eastview"], days=1, hours=1)
    assert "(NSDROP) Connecting to ftp.nsdrop.com via SFTP client" in caplog.text
    assert "(EASTVIEW) Connecting to ftp.eastview.com via SFTP client" in caplog.text
    assert "(EASTVIEW) 0 file(s) on EASTVIEW server to copy to NSDROP" in caplog.text
    assert "(EASTVIEW) Client session closed" in caplog.text
    assert "(NSDROP) Client session closed" in caplog.text


def test_validate_files(mock_Client, caplog):
    validate_files(vendor="eastview", files=None)
    assert "(NSDROP) Connecting to " in caplog.text
    assert "(NSDROP) Validating eastview file: bar.mrc" in caplog.text


def test_validate_files_with_list(mock_Client, caplog):
    validate_files(vendor="eastview", files=["foo.mrc"])
    assert "(NSDROP) Connecting to " in caplog.text
    assert "(NSDROP) Validating eastview file: foo.mrc" in caplog.text
