import datetime
import io
import logging
import os
from googleapiclient.errors import HttpError  # type: ignore
from pydantic_core import ValidationError, InitErrorDetails
from pymarc import Record, Field, Subfield
import pytest
from click.testing import CliRunner
from file_retriever.file import File, FileInfo
from file_retriever.connect import Client
from file_retriever._clients import _ftpClient, _sftpClient
from record_validator.marc_models import RecordModel
from vendor_file_cli.utils import create_logger_dict


class MockFileInfo(FileInfo):
    def __init__(self, file_name: str | None = None):
        today = datetime.datetime.now(tz=datetime.timezone.utc)
        mtime = (today - datetime.timedelta(days=10)).timestamp()
        if file_name is None:
            file_name = "foo.mrc"
        super().__init__(file_name, mtime, 33188, 140401, 0, 0, None)


@pytest.fixture
def stub_record():
    bib = Record()
    bib.leader = "00454cam a22001575i 4500"
    bib.add_field(Field(tag="001", data="on1381158740"))
    bib.add_field(
        Field(
            tag="852",
            indicators=["8", " "],
            subfields=[
                Subfield(code="h", value="ReCAP 23-100000"),
            ],
        )
    )
    return bib


@pytest.fixture
def stub_file_info() -> FileInfo:
    return MockFileInfo(file_name="foo.mrc")


@pytest.fixture
def stub_file(stub_file_info, stub_record, mock_valid_record):
    return File.from_fileinfo(stub_file_info, io.BytesIO(stub_record.as_marc21()))


@pytest.fixture
def mock_valid_record(monkeypatch, stub_record):
    def mock_validation(*args, **kwargs):
        pass

    monkeypatch.setattr(RecordModel, "__init__", mock_validation)
    return stub_record


@pytest.fixture
def mock_invalid_record(monkeypatch, stub_record):
    def mock_validation(*args, **kwargs):
        raise ValidationError.from_exception_data(
            "list", [InitErrorDetails(type="missing", loc=("fields", "960"), msg="foo")]
        )

    monkeypatch.setattr(RecordModel, "__init__", mock_validation)
    return stub_record


class MockSession:
    def _check_dir(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

    def get_file_data(self, file_name, *args, **kwargs) -> FileInfo:
        return MockFileInfo(file_name=file_name)

    def write_file(self, file, *args, **kwargs) -> FileInfo:
        return MockFileInfo(file_name=file.file_name)


@pytest.fixture
def mock_Client(monkeypatch, stub_file_info, stub_record, mock_sheet_config):
    original_connect_to_server = Client._Client__connect_to_server

    def mock_login(*args, **kwargs):
        pass

    def mock_check_file(*args, **kwargs) -> bool:
        return False

    def mock_connect_to_server(self, username, password):
        original_connect_to_server(self, username, password)
        return MockSession()

    def mock_fetch_file(*args, **kwargs):
        return File.from_fileinfo(stub_file_info, io.BytesIO(stub_record.as_marc21()))

    def mock_list_file_info(*args, **kwargs):
        if isinstance(args[0], Client) and args[0].name == "NSDROP":
            return [MockFileInfo(file_name="bar.mrc")]
        else:
            return [MockFileInfo(file_name="foo.mrc")]

    def mock_list_files(*args, **kwargs):
        if isinstance(args[0], Client) and args[0].name == "NSDROP":
            return ["bar.mrc"]
        else:
            return ["foo.mrc"]

    monkeypatch.setattr(_ftpClient, "_connect_to_server", mock_login)
    monkeypatch.setattr(_sftpClient, "_connect_to_server", mock_login)
    monkeypatch.setattr(Client, "_Client__connect_to_server", mock_connect_to_server)
    monkeypatch.setattr(Client, "check_file", mock_check_file)
    monkeypatch.setattr(Client, "get_file", mock_fetch_file)
    monkeypatch.setattr(Client, "is_file", True)
    monkeypatch.setattr(Client, "list_file_info", mock_list_file_info)
    monkeypatch.setattr(Client, "list_files", mock_list_files)


@pytest.fixture
def mock_vendor_creds() -> dict:
    vendors = [
        "NSDROP",
        "EASTVIEW",
        "LEILA",
        "MIDWEST_NYPL",
        "BAKERTAYLOR_BPL",
    ]
    vars = {}
    for vendor in vendors:
        vars[f"{vendor}_HOST"] = f"ftp.{vendor.lower()}.com"
        vars[f"{vendor}_USER"] = f"{vendor.lower()}"
        vars[f"{vendor}_PASSWORD"] = "bar"
        vars[f"{vendor}_SRC"] = f"{vendor.lower()}_src"
        vars[f"{vendor}_PORT"] = "21"
    vars["NSDROP_PORT"] = "22"
    vars["EASTVIEW_PORT"] = "22"
    for k, v in vars.items():
        os.environ[k] = v
    return vars


@pytest.fixture
def mock_open_file(mock_vendor_creds, mocker):
    vendor_list = [f"{k}: {v}\n" for k, v in mock_vendor_creds.items()]
    yaml_string = "".join(vendor_list)
    m = mocker.mock_open(read_data=yaml_string)
    mocker.patch("vendor_file_cli.utils.open", m)


@pytest.fixture
def cli_runner(monkeypatch, mock_Client):
    runner = CliRunner()

    def mock_logging(*args, **kwargs):
        logger_dict = create_logger_dict()
        del logger_dict["handlers"]["file"]
        del logger_dict["handlers"]["loggly"]
        loggers = {"handlers": ["stream"], "level": "DEBUG", "propagate": False}
        logger_dict["loggers"] = {"file_retriever.vendor_file_cli": loggers}
        logger_dict["loggers"] = {"file_retriever": loggers}
        return logger_dict

    monkeypatch.setattr("vendor_file_cli.configure_logger", mock_logging)
    return runner


class MockCreds:
    def __init__(self):
        self.token = "foo"
        self.refresh_token = "bar"

    @property
    def valid(self, *args, **kwargs):
        return True

    @property
    def expired(self, *args, **kwargs):
        return False

    def refresh(self, *args, **kwargs):
        self.expired = False
        self.valid = True

    def to_json(self, *args, **kwargs):
        pass

    def run_local_server(self, *args, **kwargs):
        return self


@pytest.fixture
def mock_sheet_config(monkeypatch, caplog, mock_open_file):
    def get_creds(*args, **kwargs):
        return MockCreds()

    def build_sheet(*args, **kwargs):
        return MockResource()

    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("USERPROFILE", "test")
    monkeypatch.setattr("googleapiclient.discovery.build", build_sheet)
    monkeypatch.setattr("googleapiclient.discovery.build_from_document", build_sheet)
    monkeypatch.setattr(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        get_creds,
    )


@pytest.fixture
def mock_sheet_config_creds_invalid(monkeypatch, mock_sheet_config):
    monkeypatch.setattr(MockCreds, "valid", False)
    monkeypatch.setattr(MockCreds, "expired", True)


@pytest.fixture
def mock_sheet_config_no_creds(monkeypatch, mock_sheet_config):
    def mock_flow(*args, **kwargs):
        return MockCreds()

    def auth_user_file(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file", mock_flow
    )
    monkeypatch.setattr(
        "google_auth_oauthlib.flow.InstalledAppFlow.from_client_config", mock_flow
    )
    monkeypatch.setattr(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        auth_user_file,
    )


class MockResource:
    def __init__(self):
        self.spreadsheetId = "foo"
        self.range = "bar"

    def append(self, *args, **kwargs):
        return self

    def execute(self, *args, **kwargs):
        return {
            "spreadsheetId": "foo",
            "tableRange": "bar",
        }

    def spreadsheets(self, *args, **kwargs):
        return self

    def values(self, *args, **kwargs):
        return self


class MockError:
    def __init__(self):
        self.status = 400
        self.reason = "bad_request"


@pytest.fixture
def mock_sheet_http_error(monkeypatch):
    def mock_error(*args, **kwargs):
        raise HttpError(
            resp=MockError(),
            content=b"{'error': {'message':  'Bad Request'}}",
            uri="foo",
        )

    monkeypatch.setattr("googleapiclient.discovery.build", mock_error)
    monkeypatch.setattr("googleapiclient.discovery.build_from_document", mock_error)


@pytest.fixture
def mock_sheet_timeout_error(monkeypatch):
    def mock_error(*args, **kwargs):
        raise TimeoutError("Connection timed out")

    monkeypatch.setattr("googleapiclient.discovery.build", mock_error)
    monkeypatch.setattr("googleapiclient.discovery.build_from_document", mock_error)
