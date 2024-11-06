import datetime
import ftplib
import io
import os
from pydantic_core import ValidationError, InitErrorDetails
from pymarc import Record, Field, Subfield, Indicators
import pytest
from click.testing import CliRunner
from file_retriever.file import File, FileInfo
from file_retriever.connect import Client


@pytest.fixture(autouse=True)
def set_caplog_level(caplog):
    caplog.set_level("DEBUG")


class StubFileInfo(FileInfo):
    def __init__(self, file_name: str | None = None):
        today = datetime.datetime.now(tz=datetime.timezone.utc)
        mtime = (today - datetime.timedelta(days=10)).timestamp()
        if file_name is None:
            file_name = "foo.mrc"
        super().__init__(file_name, mtime, 33188, 140401, 0, 0, None)


def stub_marc() -> Record:
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
    return stub_marc()


@pytest.fixture
def stub_file_info() -> FileInfo:
    return StubFileInfo(file_name="foo.mrc")


@pytest.fixture
def stub_file(stub_file_info, mock_valid_record) -> File:
    return File.from_fileinfo(stub_file_info, io.BytesIO(stub_marc().as_marc21()))


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

    def _is_file(self, dir, file_name, *args, **kwargs) -> bool:
        return True

    def close(self, *args, **kwargs):
        pass

    def fetch_file(self, file, *args, **kwargs) -> File:
        return File.from_fileinfo(file, io.BytesIO(stub_marc().as_marc21()))

    def get_file_data(self, file_name, *args, **kwargs) -> FileInfo:
        return StubFileInfo(file_name=file_name)

    def is_active(self, *args, **kwargs) -> bool:
        return True

    def list_file_data(self, dir, *args, **kwargs) -> list[FileInfo]:
        if "NSDROP" in dir:
            return [StubFileInfo(file_name="bar.mrc")]
        else:
            return [StubFileInfo(file_name="foo.mrc")]

    def list_file_names(self, dir, *args, **kwargs) -> list[str]:
        if "NSDROP" in dir:
            return ["bar.mrc"]
        elif "midwest" or "MIDWEST" in dir:
            return ["NYP_10012024_ALL_01.mrc"]
        else:
            return ["foo.mrc"]

    def write_file(self, file, *args, **kwargs) -> FileInfo:
        return StubFileInfo(file_name=file.file_name)


@pytest.fixture
def stub_client(monkeypatch, mock_sheet_config):
    original_connect_to_server = Client._Client__connect_to_server

    def mock_connect_to_server(self, username, password):
        original_connect_to_server(self, username, password)
        return MockSession()

    def stub_response(*args, **kwargs):
        pass

    monkeypatch.setattr("ftplib.FTP.connect", stub_response)
    monkeypatch.setattr("ftplib.FTP.login", stub_response)
    monkeypatch.setattr("paramiko.SSHClient.connect", stub_response)
    monkeypatch.setattr("paramiko.SSHClient.load_system_host_keys", stub_response)
    monkeypatch.setattr("paramiko.SSHClient.open_sftp", stub_response)
    monkeypatch.setattr(Client, "_Client__connect_to_server", mock_connect_to_server)
    monkeypatch.setattr(Client, "check_file", lambda *args, **kwargs: False)
    monkeypatch.setattr("vendor_file_cli.validator.write_data_to_sheet", stub_response)
    monkeypatch.setattr(os.path, "isfile", lambda *args, **kwargs: True)

    def stub_client_response(name):
        return Client(
            name=name.upper(),
            username=os.environ[f"{name.upper()}_USER"],
            password=os.environ[f"{name.upper()}_PASSWORD"],
            host=os.environ[f"{name.upper()}_HOST"],
            port=os.environ[f"{name.upper()}_PORT"],
        )

    return stub_client_response


@pytest.fixture
def stub_client_auth_error(monkeypatch, stub_client):
    def mock_connect_to_server(*args, **kwargs):
        raise ftplib.error_perm

    monkeypatch.setattr("ftplib.FTP.login", mock_connect_to_server)


@pytest.fixture
def mock_vendor_creds() -> str:
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
    return yaml_string


@pytest.fixture
def mock_open_file(mock_vendor_creds, mocker) -> None:
    m = mocker.mock_open(read_data=mock_vendor_creds)
    mocker.patch("vendor_file_cli.utils.open", m)
    mocker.patch.dict(os.environ, {"USERPROFILE": "test"})
    mocker.patch("os.path.exists", lambda *args, **kwargs: True)


@pytest.fixture
def unset_env_var(monkeypatch, mock_vendor_creds) -> None:
    keys = ["NSDROP", "EASTVIEW", "LEILA", "MIDWEST_NYPL", "BAKERTAYLOR_BPL", "LOGGLY"]
    env_vars = os.environ.keys()
    for var in env_vars:
        if any(key in var for key in keys):
            monkeypatch.delenv(var, raising=False)


@pytest.fixture
def cli_runner(monkeypatch, stub_client) -> CliRunner:
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
def mock_sheet_config(monkeypatch, mock_open_file):
    def build_sheet(*args, **kwargs):
        return MockResource()

    monkeypatch.setattr("googleapiclient.discovery.build", build_sheet)
    monkeypatch.setattr("googleapiclient.discovery.build_from_document", build_sheet)
    monkeypatch.setattr(
        "google.oauth2.credentials.Credentials.from_authorized_user_info",
        lambda *args, **kwargs: MockCreds(),
    )
    monkeypatch.setattr("vendor_file_cli.utils.load_creds", lambda *args: None)
    monkeypatch.setenv("GOOGLE_SHEET_TOKEN", "foo")
    monkeypatch.setenv("GOOGLE_SHEET_REFRESH_TOKEN", "bar")
    monkeypatch.setenv("GOOGLE_SHEET_CLIENT_ID", "baz")
    monkeypatch.setenv("GOOGLE_SHEET_CLIENT_SECRET", "qux")


@pytest.fixture
def mock_sheet_config_creds_invalid(monkeypatch, mock_sheet_config):
    monkeypatch.setattr(MockCreds, "valid", False)
    monkeypatch.setattr(MockCreds, "expired", True)


@pytest.fixture
def mock_sheet_config_no_creds(monkeypatch, mock_sheet_config):
    monkeypatch.setattr(
        "google_auth_oauthlib.flow.InstalledAppFlow.from_client_config",
        lambda *args, **kwargs: MockCreds(),
    )
    monkeypatch.setattr(
        "google.oauth2.credentials.Credentials.from_authorized_user_info",
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


@pytest.fixture
def mock_sheet_timeout_error(monkeypatch):
    def mock_error(*args, **kwargs):
        raise TimeoutError("Connection timed out")

    monkeypatch.setattr("googleapiclient.discovery.build", mock_error)
    monkeypatch.setattr("googleapiclient.discovery.build_from_document", mock_error)
