import logging
import os
from click.testing import CliRunner
import pytest
from vendor_file_cli import vendor_file_cli, main


def test_main(mocker):
    mock_main = mocker.Mock()
    mocker.patch("vendor_file_cli.main", return_value=mock_main)
    with pytest.raises(SystemExit):
        main()


def test_vendor_file_cli():
    runner = CliRunner()
    runner.invoke(vendor_file_cli)
    assert runner.get_default_prog_name(vendor_file_cli) == "vendor-file-cli"


def test_vendor_file_cli_get_all_vendor_files(cli_runner, caplog):
    result = cli_runner.invoke(cli=vendor_file_cli, args=["all-vendor-files"])
    assert result.exit_code == 0
    assert "(NSDROP) Connecting to " in caplog.text
    assert "(EASTVIEW) Connecting to " in caplog.text
    assert "(EASTVIEW) Client session closed" in caplog.text
    assert "(MIDWEST_NYPL) Connecting to " in caplog.text
    assert "(MIDWEST_NYPL) Client session closed" in caplog.text


def test_vendor_file_cli_get_all_vendor_files_no_creds(mocker, cli_runner, caplog):
    mocker.patch.dict(os.environ, {}, clear=True)
    cli_runner.invoke(cli=vendor_file_cli, args=["all-vendor-files"])
    assert (
        "vendor_file_cli",
        10,
        "Vendor credentials not in environment variables. Loading from file.",
    ) in caplog.record_tuples
    assert (
        "vendor_file_cli.utils",
        40,
        "Vendor credentials file not found.",
    ) in caplog.record_tuples


def test_vendor_file_cli_get_all_vendor_files_test(cli_runner, caplog):
    logger = logging.getLogger("vendor_file_cli")
    loggly = logging.NullHandler()
    loggly.name = "loggly"
    logger.addHandler(loggly)
    result = cli_runner.invoke(cli=vendor_file_cli, args=["all-vendor-files", "--test"])
    assert result.exit_code == 0
    assert "Running in test mode" in caplog.text
    assert logger.handlers == []


def test_vendor_file_cli_get_available_vendors(cli_runner):
    result = cli_runner.invoke(cli=vendor_file_cli, args=["available-vendors"])
    assert result.exit_code == 0
    assert "Available vendors: " in result.stdout
    assert (
        "Available vendors: ['EASTVIEW', 'LEILA', 'MIDWEST_NYPL', 'BAKERTAYLOR_BPL']"
        in result.stdout
    )


def test_vendor_file_cli_get_recent_vendor_files(cli_runner, caplog):
    cli_runner.invoke(
        cli=vendor_file_cli,
        args=["vendor-files", "-v", "all"],
    )
    assert "(NSDROP) Connecting to " in caplog.text
    assert "(EASTVIEW) Connecting to " in caplog.text
    assert "(EASTVIEW) Client session closed" in caplog.text


def test_vendor_file_cli_get_recent_vendor_files_multiple_vendors(cli_runner, caplog):
    result = cli_runner.invoke(
        cli=vendor_file_cli,
        args=["vendor-files", "-v", "eastview", "-v", "leila"],
    )
    assert result.exit_code == 0
    assert "(NSDROP) Connecting to " in caplog.text
    assert "(EASTVIEW) Connecting to " in caplog.text
    assert "(EASTVIEW) Client session closed" in caplog.text
    assert "(LEILA) Connecting to " in caplog.text
    assert "(LEILA) Client session closed" in caplog.text


def test_vendor_file_cli_validate_vendor_files(cli_runner, caplog):
    result = cli_runner.invoke(
        cli=vendor_file_cli,
        args=["validate-file", "-v", "eastview", "-f", "foo.mrc"],
    )
    assert result.exit_code == 0
    assert "(NSDROP) Connecting to " in caplog.text
    assert "(NSDROP) Validating eastview file: foo.mrc" in caplog.text


def test_vendor_file_cli_validate_vendor_files_invalid_vendor(cli_runner, caplog):
    result = cli_runner.invoke(
        cli=vendor_file_cli,
        args=["validate-file", "-v", "foo", "-f", "foo.mrc"],
    )
    assert result.exit_code == 0
    assert (
        "Vendor not supported for validation."
        "Only EASTVIEW, LEILA, and AMALIVRE_SASB supported." in result.stdout
    )


def test_vendor_file_cli_validate_vendor_files_test(cli_runner, caplog):
    logger = logging.getLogger("vendor_file_cli")
    loggly = logging.NullHandler()
    loggly.name = "loggly"
    logger.addHandler(loggly)
    result = cli_runner.invoke(
        cli=vendor_file_cli,
        args=["validate-file", "-v", "eastview", "-f", "foo.mrc", "--test"],
    )
    assert result.exit_code == 0
    assert "(NSDROP) Connecting to " in caplog.text
    assert "(NSDROP) Validating eastview file: foo.mrc" in caplog.text
    assert result.exit_code == 0
    assert "Running in test mode" in caplog.text
    assert logger.handlers == []
