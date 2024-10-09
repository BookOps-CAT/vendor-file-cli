import logging
import logging.config
import logging.handlers
import os
import pytest
from vendor_file_cli.config import (
    load_vendor_creds,
    logger_config,
)


def test_logger_config():
    cli_logger = logging.getLogger("vendor_file_cli")
    while cli_logger.handlers:
        handler = cli_logger.handlers[0]
        cli_logger.removeHandler(handler)
        handler.close()
    logger_config(cli_logger)
    config_handlers = cli_logger.handlers
    handler_types = [type(i) for i in config_handlers]
    assert len(handler_types) == 2
    assert handler_types == [
        logging.StreamHandler,
        logging.handlers.RotatingFileHandler,
    ]
    assert config_handlers[0].level == 10
    assert (
        config_handlers[0].formatter._fmt == "%(asctime)s - %(levelname)s - %(message)s"
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


def test_load_vendor_creds_empty_yaml(mocker):
    yaml_string = ""
    m = mocker.mock_open(read_data=yaml_string)
    mocker.patch("builtins.open", m)

    with pytest.raises(ValueError) as exc:
        load_vendor_creds("foo.yaml")
    assert "No credentials found in config file" in str(exc.value)


@pytest.mark.livetest
def test_client_config_live():
    client_list = load_vendor_creds(
        os.path.join(os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml")
    )
    assert len(client_list) > 1
    assert "LEILA" in client_list
