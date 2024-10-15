import os
import pytest
from file_retriever.connect import Client
from vendor_file_cli.commands import (
    connect,
    get_vendor_files,
    get_single_file,
    validate_files,
)
from vendor_file_cli.config import load_vendor_creds


def test_connect(mock_Client, mocker):
    yaml_string = """
        FOO_HOST: ftp.testvendor.com
        FOO_USER: bar
        FOO_PASSWORD: baz
        FOO_PORT: '21'
        FOO_SRC: foo_src
        FOO_DST: foo_dst
    """
    m = mocker.mock_open(read_data=yaml_string)
    mocker.patch("builtins.open", m)

    load_vendor_creds("foo.yaml")
    client = connect("foo")
    assert client.name == "FOO"
    assert client.host == "ftp.testvendor.com"
    assert client.port == "21"
    assert isinstance(client, Client)
    assert client.session is not None


def test_get_vendor_files(mock_Client, caplog):
    (
        os.environ["NSDROP_HOST"],
        os.environ["NSDROP_USER"],
        os.environ["NSDROP_PASSWORD"],
        os.environ["NSDROP_PORT"],
        os.environ["NSDROP_SRC"],
    ) = ("sftp.foo.com", "foo", "bar", "22", "foo_src")
    vendors = ["foo"]
    get_vendor_files(vendors=vendors, days=300)
    assert "(NSDROP) Connected to server" in caplog.text
    assert "(FOO) Connected to server" in caplog.text
    assert "(FOO) Retrieving list of files in " in caplog.text
    assert "(FOO) 1 recent file(s) in `foo_src`" in caplog.text
    assert "(FOO) Closing client session" in caplog.text
    assert (
        "(NSDROP) Checking list of 1 files against `NSDROP/vendor_records/foo`"
        in caplog.text
    )
    assert (
        "(NSDROP) 1 of 1 files missing from `NSDROP/vendor_records/foo`" in caplog.text
    )
    assert "(FOO) Fetching foo.mrc from `foo_src`" in caplog.text
    assert (
        "(NSDROP) Checking for file in `NSDROP/vendor_records/foo` before writing"
        in caplog.text
    )
    assert "(NSDROP) Writing foo.mrc to `NSDROP/vendor_records/foo`" in caplog.text


def test_get_vendor_files_no_files(mock_Client, caplog):
    get_vendor_files(vendors=["eastview"], days=1, hours=1)
    assert "(NSDROP) Connected to server" in caplog.text
    assert "(EASTVIEW) Connected to server" in caplog.text
    assert "(EASTVIEW) Retrieving list of files in " in caplog.text
    assert "(EASTVIEW) 0 recent file(s) in `eastview_src`" in caplog.text
    assert "(EASTVIEW) Closing client session" in caplog.text


def test_get_single_file_no_validation(mock_Client, stub_file_info, caplog):
    vendor_client = connect("eastview")
    nsdrop_client = connect("nsdrop")
    get_single_file(
        vendor="eastview",
        file=stub_file_info,
        vendor_client=vendor_client,
        nsdrop_client=nsdrop_client,
    )
    assert "(EASTVIEW) Connected to server" in caplog.text
    assert "(NSDROP) Connected to server" in caplog.text
    assert "(EASTVIEW) Fetching foo.mrc from `eastview_src`" in caplog.text
    assert (
        "(NSDROP) Checking for file in `NSDROP/vendor_records/eastview` before writing"
        in caplog.text
    )
    assert "(NSDROP) Writing foo.mrc to `NSDROP/vendor_records/eastview`" in caplog.text


def test_get_single_file_with_validation(mock_Client, stub_file_info, caplog):
    vendor_client = connect("eastview")
    nsdrop_client = connect("nsdrop")
    get_single_file(
        vendor="eastview",
        file=stub_file_info,
        vendor_client=vendor_client,
        nsdrop_client=nsdrop_client,
    )
    assert "(EASTVIEW) Connected to server" in caplog.text
    assert "(NSDROP) Connected to server" in caplog.text
    assert "(EASTVIEW) Fetching foo.mrc from `eastview_src`" in caplog.text
    assert "(NSDROP) Validating eastview file: foo.mrc" in caplog.text
    assert (
        "(NSDROP) Checking for file in `NSDROP/vendor_records/eastview` before writing"
        in caplog.text
    )
    assert "(NSDROP) Writing foo.mrc to `NSDROP/vendor_records/eastview`" in caplog.text


def test_validate_files(mock_Client, caplog):
    validate_files(vendor="eastview", files=None)
    assert (
        "(NSDROP) Retrieving list of files in `NSDROP/vendor_records/eastview`"
        in caplog.text
    )
    assert "(NSDROP) 1 file(s) in `NSDROP/vendor_records/eastview`" in caplog.text
    assert (
        "(NSDROP) Fetching foo.mrc from `NSDROP/vendor_records/eastview`" in caplog.text
    )
    assert "(NSDROP) Validating eastview file: foo.mrc" in caplog.text


def test_validate_files_with_list(mock_Client, caplog):
    validate_files(vendor="eastview", files=["foo.mrc", "bar.mrc"])
    assert (
        "(NSDROP) Fetching foo.mrc from `NSDROP/vendor_records/eastview`" in caplog.text
    )
    assert (
        "(NSDROP) Fetching bar.mrc from `NSDROP/vendor_records/eastview`" in caplog.text
    )
    assert "(NSDROP) Validating eastview file: foo.mrc" in caplog.text


@pytest.mark.livetest
def test_client_config_live():
    client_list = load_vendor_creds(
        os.path.join(os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml")
    )
    assert len(client_list) > 1
    assert "LEILA" in client_list
