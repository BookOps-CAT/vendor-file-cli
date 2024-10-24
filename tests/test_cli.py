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


def test_vendor_file_cli_get_available_vendors(cli_runner):
    result = cli_runner.invoke(cli=vendor_file_cli, args=["available-vendors"])
    assert result.exit_code == 0
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
