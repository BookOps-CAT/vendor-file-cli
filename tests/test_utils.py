import logging
import logging.config
import logging.handlers
import os
import pytest
from vendor_file_cli.utils import (
    configure_logger,
    create_logger_dict,
    load_vendor_creds,
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
