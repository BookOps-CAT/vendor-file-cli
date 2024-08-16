from click.testing import CliRunner
import pytest
from vendor_file_cli import vendor_file_cli, main


def test_main(mocker):
    mock_main = mocker.Mock()
    mocker.patch("vendor_file_cli.main", return_value=mock_main)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_vendor_file_cli():
    runner = CliRunner()
    runner.invoke(vendor_file_cli)
    assert runner.get_default_prog_name(vendor_file_cli) == "vendor-file-cli"


def test_vendor_file_cli_available_vendors(mocker, mock_yaml):
    m = mocker.mock_open(read_data=mock_yaml)
    mocker.patch("builtins.open", m)
    runner = CliRunner()
    result = runner.invoke(
        cli=vendor_file_cli,
        args=["available-vendors"],
    )
    assert "Available vendors: ['FOO', 'BAR', 'BAZ', 'NSDROP']" in result.output


def test_vendor_file_cli_available_vendors_no_vendors(mocker):
    m = mocker.mock_open(read_data="")
    mocker.patch("builtins.open", m)
    runner = CliRunner()
    result = runner.invoke(
        cli=vendor_file_cli,
        args=["available-vendors"],
    )
    assert "No vendors available." in result.output


def test_vendor_file_cli_cli_daily_vendor_files(mock_Client, mocker, caplog, mock_yaml):
    m = mocker.mock_open(read_data=mock_yaml)
    mocker.patch("builtins.open", m)
    runner = CliRunner()
    runner.invoke(
        cli=vendor_file_cli,
        args=["daily-vendor-files"],
    )
    assert "(NSDROP) Connecting to ftp.nsdrop.com" in caplog.text
    assert "(FOO) Connected to server" in caplog.text
    assert "(FOO) Retrieving list of files in " in caplog.text
    assert "(FOO) Closing client session" in caplog.text
    assert "(BAR) Connected to server" in caplog.text
    assert "(BAR) Retrieving list of files in " in caplog.text
    assert "(BAR) Closing client session" in caplog.text
    assert "(BAZ) Connected to server" in caplog.text
    assert "(BAZ) Retrieving list of files in " in caplog.text
    assert "(BAZ) Closing client session" in caplog.text


def test_vendor_file_cli_cli_get_files(mock_Client, mocker, caplog, mock_yaml):
    m = mocker.mock_open(read_data=mock_yaml)
    mocker.patch("builtins.open", m)
    runner = CliRunner()
    runner.invoke(
        cli=vendor_file_cli,
        args=["vendor-files", "-v", "all"],
    )
    assert "(NSDROP) Connecting to ftp.nsdrop.com" in caplog.text
    assert "(FOO) Connected to server" in caplog.text
    assert "(FOO) Retrieving list of files in " in caplog.text
    assert "(FOO) Closing client session" in caplog.text


def test_vendor_file_cli_cli_get_files_multiple_vendors(
    mock_Client, mocker, caplog, mock_yaml
):
    m = mocker.mock_open(read_data=mock_yaml)
    mocker.patch("builtins.open", m)
    runner = CliRunner()
    runner.invoke(
        cli=vendor_file_cli,
        args=["vendor-files", "-v", "foo", "-v", "bar", "-v", "baz"],
    )
    assert "(NSDROP) Connecting to ftp.nsdrop.com" in caplog.text
    assert "(FOO) Connected to server" in caplog.text
    assert "(FOO) Retrieving list of files in " in caplog.text
    assert "(FOO) Closing client session" in caplog.text
    assert "(BAR) Connected to server" in caplog.text
    assert "(BAR) Retrieving list of files in " in caplog.text
    assert "(BAR) Closing client session" in caplog.text
    assert "(BAZ) Connected to server" in caplog.text
    assert "(BAZ) Retrieving list of files in " in caplog.text
    assert "(BAZ) Closing client session" in caplog.text


@pytest.mark.livetest
def test_vendor_file_cli_live_available_vendors():
    runner = CliRunner()
    result = runner.invoke(
        cli=vendor_file_cli,
        args=["available-vendors"],
    )
    assert "Available vendors: " in result.output
