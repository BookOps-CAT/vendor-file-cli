import os
from pymarc import Field, Subfield
import pytest
from file_retriever.connect import Client
from vendor_file_cli.utils import (
    configure_sheet,
    connect,
    create_logger_dict,
    get_control_number,
    get_vendor_list,
    load_creds,
    read_marc_file_stream,
    write_data_to_sheet,
)


def test_configure_sheet_success(mock_sheet_config):
    creds = configure_sheet()
    assert creds.token == "foo"
    assert creds.valid is True
    assert creds.expired is False
    assert creds.refresh_token is not None


def test_configure_sheet_expired(mock_sheet_config_expired_creds):
    creds = configure_sheet()
    assert creds.token == "foo"
    assert creds.valid is True
    assert creds.expired is False
    assert creds.refresh_token is not None


def test_configure_sheet_generate_new_creds(mock_sheet_config_no_creds, caplog):
    creds = configure_sheet()
    assert creds.token == "foo"
    assert creds.valid is True
    assert creds.expired is False
    assert creds.refresh_token is not None
    assert (
        "Token for Google Sheet API not found. Running credential config flow."
        in caplog.text
    )


def test_configure_sheet_no_creds(mock_sheet_config_no_creds, caplog):
    creds = configure_sheet()
    assert creds.token == "foo"
    assert creds.valid is True
    assert creds.expired is False
    assert creds.refresh_token is not None
    assert (
        "Token for Google Sheet API not found. Running credential config flow."
        in caplog.text
    )


def test_configure_sheet_invalid_creds(mock_sheet_config_invalid_creds, caplog):
    with pytest.raises(ValueError):
        configure_sheet()


def test_connect(stub_client):
    client = connect("leila")
    assert client.name == "LEILA"
    assert client.host == "ftp.leila.com"
    assert client.port == "21"
    assert isinstance(client, Client)
    assert client.session is not None


def test_create_logger_dict(cli_runner):
    logger_dict = create_logger_dict()
    assert sorted(list(logger_dict["formatters"].keys())) == sorted(["basic", "json"])
    assert sorted(list(logger_dict["handlers"].keys())) == sorted(
        ["stream", "file", "loggly"]
    )
    assert sorted(list(logger_dict["loggers"].keys())) == sorted(
        ["file_retriever", "vendor_file_cli"]
    )


def test_get_control_number(stub_record):
    control_no = get_control_number(stub_record)
    assert control_no == "on1381158740"


@pytest.mark.parametrize(
    "field",
    ["020", "035", "022", "024", "010"],
)
def test_get_control_number_other_tag(stub_record, field):
    stub_record.remove_fields("001")
    stub_record.add_ordered_field(
        Field(
            tag=field,
            indicators=[" ", " "],
            subfields=[
                Subfield(code="a", value="foo"),
            ],
        )
    )
    control_no = get_control_number(stub_record)
    assert control_no == "foo"


def test_get_control_number_skip_invalid_isbn(stub_record):
    stub_record.remove_fields("001")
    stub_record.add_ordered_field(
        Field(
            tag="020",
            indicators=[" ", " "],
            subfields=[
                Subfield(code="z", value="foo"),
            ],
        )
    )
    stub_record.add_ordered_field(
        Field(
            tag="035",
            indicators=[" ", " "],
            subfields=[
                Subfield(code="a", value="bar"),
            ],
        )
    )
    control_no = get_control_number(stub_record)
    assert control_no == "bar"


def test_get_control_number_call_no(stub_record):
    stub_record.remove_fields("001")
    control_no = get_control_number(stub_record)
    assert control_no == "ReCAP 23-100000"


def test_get_control_number_none(stub_record):
    stub_record.remove_fields("001", "852")
    control_no = get_control_number(stub_record)
    assert control_no == "None"


def test_get_vendor_list():
    vendor_list = get_vendor_list()
    assert sorted(vendor_list) == sorted(
        ["LEILA", "MIDWEST_NYPL", "BAKERTAYLOR_BPL", "EASTVIEW"]
    )


def test_get_vendor_list_no_env_vars_set(unset_env_var):
    with pytest.raises(ValueError) as exc:
        get_vendor_list()
    assert "No vendors found in environment variables." in str(exc.value)


def test_load_creds(mock_open_file):
    load_creds()
    assert os.environ["NSDROP_HOST"] == "ftp.nsdrop.com"
    assert os.environ["NSDROP_PORT"] == "22"
    assert os.environ["LEILA_HOST"] == "ftp.leila.com"
    assert os.environ["LEILA_PORT"] == "21"
    assert os.environ["LEILA_SRC"] == "leila_src"
    assert os.environ["LEILA_DST"] == "NSDROP/vendor_records/leila"


def test_load_creds_empty_yaml(mocker):
    yaml_string = ""
    m = mocker.mock_open(read_data=yaml_string)
    mocker.patch("builtins.open", m)
    mocker.patch("os.path.exists", lambda *args, **kwargs: True)
    with pytest.raises(ValueError) as exc:
        load_creds("foo.yaml")
    assert "No credentials found in config file" in str(exc.value)


def test_load_creds_no_userprofile_env_var(mocker):
    mocker.patch.dict(os.environ, {}, clear=True)
    with pytest.raises(ValueError) as exc:
        load_creds()
    assert "Vendor credentials file not found." in str(exc.value)


def test_load_creds_file_not_found(mocker):
    mocker.patch.dict(os.environ, {"USERPROFILE": "test"})
    with pytest.raises(ValueError) as exc:
        load_creds()
    assert "Vendor credentials file not found." in str(exc.value)


def test_read_marc_file_stream(stub_file):
    stream = read_marc_file_stream(stub_file)
    assert stream is not None
    assert stream.__next__().get_fields("001")[0].data == "on1381158740"
    records = [i for i in read_marc_file_stream(stub_file)]
    assert len(records) == 1


def test_write_data_to_sheet(mock_sheet_config):
    data = write_data_to_sheet(
        {"file_name": ["foo.mrc"], "vendor_code": ["FOO"]}, test=False
    )
    keys = data.keys()
    assert sorted(list(keys)) == sorted(["spreadsheetId", "tableRange"])


def test_write_data_to_sheet_test(mock_sheet_config):
    data = write_data_to_sheet(
        {"file_name": ["foo.mrc"], "vendor_code": ["FOO"]}, test=True
    )
    keys = data.keys()
    assert sorted(list(keys)) == sorted(["spreadsheetId", "tableRange"])


def test_write_data_to_sheet_timeout_error(
    mock_sheet_config, mock_sheet_timeout_error, caplog
):
    data = write_data_to_sheet(
        {"file_name": ["foo.mrc"], "vendor_code": ["FOO"]}, test=False
    )
    assert data is None
    assert "Unable to send data to google sheet:" in caplog.text
    assert (
        "(FOO) Validation data not written to google sheet for foo.mrc." in caplog.text
    )


def test_write_data_to_sheet_auth_error(
    mock_sheet_config, mock_sheet_auth_error, caplog
):
    data = write_data_to_sheet(
        {"file_name": ["foo.mrc"], "vendor_code": ["FOO"]}, test=False
    )
    assert data is None
    assert "Unable to configure google sheet API credentials:" in caplog.text
    assert (
        "(FOO) Validation data not written to google sheet for foo.mrc." in caplog.text
    )
