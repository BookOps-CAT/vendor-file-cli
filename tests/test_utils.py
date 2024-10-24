import logging
import logging.config
import logging.handlers
import os
from pymarc import Field, Subfield
import pytest
from file_retriever.connect import Client
from vendor_file_cli.utils import (
    configure_logger,
    configure_sheet,
    connect,
    create_logger_dict,
    get_control_number,
    load_vendor_creds,
    read_marc_file_stream,
    write_data_to_sheet,
)


def test_configure_logger():
    logger_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "basic": {
                "format": "%(app_name)s-%(asctime)s-%(name)s-%(lineno)d-%(levelname)s-%(message)s",  # noqa: E501
                "defaults": {"app_name": "foo"},
            },
        },
        "handlers": {
            "stream_1": {
                "class": "logging.StreamHandler",
                "formatter": "basic",
                "level": "DEBUG",
            },
            "stream_2": {
                "class": "logging.StreamHandler",
                "formatter": "basic",
                "level": "INFO",
            },
        },
        "loggers": {
            "foo": {
                "handlers": ["stream_1", "stream_2"],
                "level": "DEBUG",
                "propagate": False,
            },
            "foo.bar": {
                "handlers": ["stream_1", "stream_2"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
    }
    configure_logger(logger_dict)
    logger = logging.getLogger("foo")
    config_handlers = logger.handlers
    handler_types = [type(i) for i in config_handlers]
    assert len(handler_types) == 2
    assert logging.StreamHandler in handler_types
    assert sorted([i.level for i in config_handlers]) == sorted([10, 20])


def test_configure_sheet_success(mock_sheet_config):
    creds = configure_sheet()
    assert creds.token == "foo"
    assert creds.valid is True
    assert creds.expired is False
    assert creds.refresh_token is not None


def test_configure_sheet_invalid(mock_sheet_config_creds_invalid):
    creds = configure_sheet()
    assert creds.token == "foo"
    assert creds.valid is True
    assert creds.expired is False
    assert creds.refresh_token is not None


def test_configure_sheet_generate_new_creds(mock_sheet_config_no_creds):
    creds = configure_sheet()
    assert creds.token == "foo"
    assert creds.valid is True
    assert creds.expired is False
    assert creds.refresh_token is not None


def test_connect(mock_Client):
    client = connect("leila")
    assert client.name == "LEILA"
    assert client.host == "ftp.leila.com"
    assert client.port == "21"
    assert isinstance(client, Client)
    assert client.session is not None


def test_create_logger_dict():
    logger_dict = create_logger_dict()
    assert sorted(list(logger_dict.keys())) == sorted(
        ["version", "disable_existing_loggers", "formatters", "handlers", "loggers"]
    )
    assert sorted(list(logger_dict["formatters"].keys())) == sorted(["basic", "json"])
    assert sorted(list(logger_dict["handlers"].keys())) == sorted(
        ["stream", "file", "loggly"]
    )
    assert sorted(list(logger_dict["loggers"].keys())) == sorted(
        ["file_retriever", "file_retriever.vendor_file_cli"]
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


def test_get_control_number_call_no(stub_record):
    stub_record.remove_fields("001")
    control_no = get_control_number(stub_record)
    assert control_no == "ReCAP 23-100000"


def test_get_control_number_none(stub_record):
    stub_record.remove_fields("001", "852")
    control_no = get_control_number(stub_record)
    assert control_no == "None"


def test_load_vendor_creds(mocker):
    yaml_string = """
        FOO_HOST: foo
        FOO_USER: bar
        FOO_PASSWORD: baz
        FOO_PORT: '21'
        FOO_SRC: foo_src
        BAR_HOST: foo
        BAR_USER: bar
        BAR_PASSWORD: baz
        BAR_PORT: '22'
        BAR_SRC: bar_src
    """
    m = mocker.mock_open(read_data=yaml_string)
    mocker.patch("builtins.open", m)

    client_list = load_vendor_creds("foo.yaml")
    assert len(client_list) == 2
    assert client_list == ["FOO", "BAR"]
    assert os.environ["FOO_HOST"] == "foo"
    assert os.environ["FOO_USER"] == "bar"
    assert os.environ["FOO_PASSWORD"] == "baz"
    assert os.environ["FOO_PORT"] == "21"
    assert os.environ["FOO_SRC"] == "foo_src"
    assert os.environ["FOO_DST"] == "NSDROP/vendor_records/foo"


def test_load_vendor_creds_empty_yaml(mocker):
    yaml_string = ""
    m = mocker.mock_open(read_data=yaml_string)
    mocker.patch("builtins.open", m)

    with pytest.raises(ValueError) as exc:
        load_vendor_creds("foo.yaml")
    assert "No credentials found in config file" in str(exc.value)


def test_read_marc_file_stream(stub_file):
    stream = read_marc_file_stream(stub_file)
    assert stream is not None
    assert stream.__next__().get_fields("001")[0].data == "on1381158740"
    records = [i for i in read_marc_file_stream(stub_file)]
    assert len(records) == 1


def test_write_data_to_sheet(mock_sheet_config):
    data = write_data_to_sheet(
        values={"file_name": ["foo.mrc"], "vendor_code": ["FOO"]}
    )
    assert sorted(list(data.keys())) == sorted(
        [
            "spreadsheetId",
            "tableRange",
        ]
    )


def test_write_data_to_sheet_http_error(
    mock_sheet_config, mock_sheet_http_error, caplog
):
    data = write_data_to_sheet(
        values={"file_name": ["foo.mrc"], "vendor_code": ["FOO"]}
    )
    assert data is None
    assert "Error occurred while sending data to google sheet: " in caplog.text


def test_write_data_to_sheet_timeout_error(
    mock_sheet_config, mock_sheet_timeout_error, caplog
):
    data = write_data_to_sheet(
        values={"file_name": ["foo.mrc"], "vendor_code": ["FOO"]}
    )
    assert data is None
    assert (
        "Error occurred while sending data to google sheet: Connection timed out"
        in caplog.text
    )
