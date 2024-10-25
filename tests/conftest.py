import datetime
import io
import logging
import os
from googleapiclient.errors import HttpError  # type: ignore
from pydantic_core import ValidationError, InitErrorDetails
from pymarc import Record, Field, Subfield, Indicators
import pytest
from click.testing import CliRunner
from file_retriever.file import File, FileInfo
from file_retriever.connect import Client
from file_retriever._clients import _ftpClient, _sftpClient


class MockFileInfo(FileInfo):
    def __init__(self, file_name: str | None = None):
        today = datetime.datetime.now(tz=datetime.timezone.utc)
        mtime = (today - datetime.timedelta(days=10)).timestamp()
        if file_name is None:
            file_name = "foo.mrc"
        super().__init__(file_name, mtime, 33188, 140401, 0, 0, None)


def mock_marc() -> Record:
    bib = Record()
    bib.leader = "00454cam a22001575i 4500"
    bib.add_field(Field(tag="001", data="on1381158740"))
    bib.add_field(
        Field(
            tag="852",
            indicators=Indicators("8", " "),
            subfields=[Subfield("h", "ReCAP 23-100000")],
        )
    )
    return bib


@pytest.fixture
def stub_record() -> Record:
    return mock_marc()


@pytest.fixture
def stub_file_info() -> FileInfo:
    return MockFileInfo(file_name="foo.mrc")


@pytest.fixture
def stub_file(stub_file_info, mock_valid_record) -> File:
    return File.from_fileinfo(stub_file_info, io.BytesIO(mock_marc().as_marc21()))


@pytest.fixture
def mock_valid_record(monkeypatch, stub_record) -> Record:
    def mock_validation(*args, **kwargs):
        pass

    monkeypatch.setattr("vendor_file_cli.validator.RecordModel", mock_validation)
    return stub_record


@pytest.fixture
def mock_invalid_record(monkeypatch, stub_record) -> Record:
    def mock_validation(*args, **kwargs):
        errors = [InitErrorDetails(type="missing", loc=("fields", "960"), msg="foo")]
        raise ValidationError.from_exception_data("list", errors)

    monkeypatch.setattr("vendor_file_cli.validator.RecordModel", mock_validation)
    return stub_record


class MockSession:
    def _check_dir(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

    def get_file_data(self, file_name, *args, **kwargs) -> FileInfo:
        return MockFileInfo(file_name=file_name)

    def list_file_data(self, dir, *args, **kwargs) -> list[FileInfo]:
        if "NSDROP" in dir:
            return [MockFileInfo(file_name="bar.mrc")]
        else:
            return [MockFileInfo(file_name="foo.mrc")]

    def list_file_names(self, dir, *args, **kwargs) -> list[str]:
        if "NSDROP" in dir:
            return ["bar.mrc"]
        elif "midwest" or "MIDWEST" in dir:
            return ["NYP_10012024_ALL_01.mrc"]
        else:
            return ["foo.mrc"]

    def fetch_file(self, file, *args, **kwargs) -> File:
        return File.from_fileinfo(file, io.BytesIO(mock_marc().as_marc21()))

    def write_file(self, file, *args, **kwargs) -> FileInfo:
        return MockFileInfo(file_name=file.file_name)


@pytest.fixture
def mock_Client(monkeypatch, mock_sheet_config):
    original_connect_to_server = Client._Client__connect_to_server

    def mock_connect_to_server(self, username, password):
        original_connect_to_server(self, username, password)
        return MockSession()

    monkeypatch.setattr(_ftpClient, "_connect_to_server", lambda *args, **kwargs: None)
    monkeypatch.setattr(_sftpClient, "_connect_to_server", lambda *args, **kwargs: None)
    monkeypatch.setattr(Client, "_Client__connect_to_server", mock_connect_to_server)
    monkeypatch.setattr(Client, "check_file", lambda *args, **kwargs: False)
    monkeypatch.setattr(Client, "is_file", True)
    monkeypatch.setattr(
        "vendor_file_cli.validator.write_data_to_sheet", lambda *args, **kwargs: None
    )


@pytest.fixture(autouse=True)
def mock_vendor_creds(monkeypatch) -> str:
    vendors = ["NSDROP", "EASTVIEW", "LEILA", "MIDWEST_NYPL", "BAKERTAYLOR_BPL"]
    env = {"LOGGLY_TOKEN": "foo"}
    for vendor in vendors:
        env[f"{vendor}_HOST"] = f"ftp.{vendor.lower()}.com"
        env[f"{vendor}_USER"] = f"{vendor.lower()}"
        env[f"{vendor}_PASSWORD"] = "bar"
        env[f"{vendor}_PORT"] = "21"
        env[f"{vendor}_SRC"] = f"{vendor.lower()}_src"
        env[f"{vendor}_DST"] = f"NSDROP/vendor_records/{vendor.lower()}"
    env["NSDROP_PORT"] = "22"
    env["EASTVIEW_PORT"] = "22"
    yaml_string = ""
    for k, v in env.items():
        os.environ[k] = v
        yaml_string += f"{k}: {v}\n"
    monkeypatch.setattr("vendor_file_cli.utils.load_creds", lambda *args: None)
    return yaml_string


@pytest.fixture
def mock_open_file(mock_vendor_creds, mocker) -> None:
    m = mocker.mock_open(read_data=mock_vendor_creds)
    mocker.patch("vendor_file_cli.utils.open", m)


@pytest.fixture
def cli_runner(monkeypatch, mock_Client) -> CliRunner:
    runner = CliRunner()

    def mock_logging(*args, **kwargs):
        logger_dict = {"version": 1, "disable_existing_loggers": False}
        str_format = (
            "vendor_file_cli-%(asctime)s-%(filename)s-%(levelname)s-%(message)s"
        )
        handler = {"class": "StreamHandler", "formatter": "basic", "level": "DEBUG"}
        logger_dict.update({"formatters": {"basic": {"format": str_format}}})
        logger_dict.update({"handlers": {"stream": handler}})
        logger_dict.update({"loggers": {}})
        logger_dict["loggers"] = {"file_retriever": {"handlers": ["stream"]}}
        logger_dict["loggers"] = {"vendor_file_cli": {"handlers": ["stream"]}}
        return logger_dict

    monkeypatch.setattr("logging.config.dictConfig", mock_logging)
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
    def build_sheet(*args, **kwargs):
        return MockResource()

    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("USERPROFILE", "test")
    monkeypatch.setattr("googleapiclient.discovery.build", build_sheet)
    monkeypatch.setattr("googleapiclient.discovery.build_from_document", build_sheet)
    monkeypatch.setattr(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        lambda *args, **kwargs: MockCreds(),
    )


@pytest.fixture
def mock_sheet_config_creds_invalid(monkeypatch, mock_sheet_config):
    monkeypatch.setattr(MockCreds, "valid", False)
    monkeypatch.setattr(MockCreds, "expired", True)


@pytest.fixture
def mock_sheet_config_no_creds(monkeypatch, mock_sheet_config):
    monkeypatch.setattr(
        "google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file",
        lambda *args, **kwargs: MockCreds(),
    )
    monkeypatch.setattr(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        lambda *args, **kwargs: None,
    )


class MockResource:
    def __init__(self):
        self.spreadsheetId = "foo"
        self.range = "bar"

    def append(self, *args, **kwargs):
        return self

    def execute(self, *args, **kwargs):
        return dict(spreadsheetId=self.spreadsheetId, tableRange=self.range)

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
            resp=MockError(), content=b"{'message':  'Bad Request'}", uri="foo"
        )

    monkeypatch.setattr("googleapiclient.discovery.build", mock_error)
    monkeypatch.setattr("googleapiclient.discovery.build_from_document", mock_error)


@pytest.fixture
def mock_sheet_timeout_error(monkeypatch):
    def mock_error(*args, **kwargs):
        raise TimeoutError("Connection timed out")

    monkeypatch.setattr("googleapiclient.discovery.build", mock_error)
    monkeypatch.setattr("googleapiclient.discovery.build_from_document", mock_error)
