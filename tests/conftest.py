import io
import os
from googleapiclient.errors import HttpError  # type: ignore
from pymarc import Record, Field, Subfield
import pytest
from click.testing import CliRunner
from file_retriever.connect import Client
from file_retriever.file import File, FileInfo


def create_marc():
    bib = Record()
    bib.leader = "00454cam a22001575i 4500"
    bib.add_field(Field(tag="001", data="on1381158740"))
    bib.add_field(Field(tag="008", data="190306s2017    ht a   j      000 1 hat d"))
    bib.add_field(
        Field(
            tag="050",
            indicators=[" ", "4"],
            subfields=[
                Subfield(code="a", value="F00"),
            ],
        )
    )
    bib.add_field(
        Field(
            tag="245",
            indicators=["0", "0"],
            subfields=[
                Subfield(code="a", value="Title :"),
            ],
        )
    )
    bib.add_field(
        Field(
            tag="300",
            indicators=[" ", " "],
            subfields=[
                Subfield(code="a", value="100 pages :"),
            ],
        )
    )
    bib.add_field(
        Field(
            tag="852",
            indicators=["8", " "],
            subfields=[
                Subfield(code="h", value="ReCAP 23-100000"),
            ],
        )
    )
    bib.add_field(
        Field(
            tag="901",
            indicators=[" ", " "],
            subfields=[
                Subfield(code="a", value="EVP"),
            ],
        )
    )
    bib.add_field(
        Field(
            tag="910",
            indicators=[" ", " "],
            subfields=[
                Subfield(code="a", value="RL"),
            ],
        )
    )
    bib.add_field(
        Field(
            tag="949",
            indicators=[" ", "1"],
            subfields=[
                Subfield(code="z", value="8528"),
                Subfield(code="a", value="ReCAP 23-100000"),
                Subfield(code="c", value="1"),
                Subfield(code="h", value="43"),
                Subfield(code="i", value="33433123456789"),
                Subfield(code="l", value="rcmf2"),
                Subfield(code="m", value="bar"),
                Subfield(code="p", value="1.00"),
                Subfield(code="t", value="55"),
                Subfield(code="u", value="foo"),
                Subfield(code="v", value="EVP"),
            ],
        )
    )
    bib.add_field(
        Field(
            tag="960",
            indicators=[" ", " "],
            subfields=[
                Subfield(code="s", value="100"),
                Subfield(code="t", value="MAF"),
                Subfield(code="u", value="123456apprv"),
            ],
        )
    )
    bib.add_field(
        Field(
            tag="980",
            indicators=[" ", " "],
            subfields=[
                Subfield(code="a", value="240101"),
                Subfield(code="b", value="100"),
                Subfield(code="c", value="100"),
                Subfield(code="d", value="000"),
                Subfield(code="e", value="200"),
                Subfield(code="f", value="123456"),
                Subfield(code="g", value="1"),
            ],
        )
    )
    return bib


@pytest.fixture
def stub_record():
    return create_marc()


def mock_file_info(file_name: FileInfo | str | None = None) -> FileInfo:
    if isinstance(file_name, FileInfo):
        return file_name
    elif file_name is None:
        file_name = "foo.mrc"
    return FileInfo(
        file_name=file_name,
        file_mtime=1704070800,
        file_mode=33188,
        file_atime=None,
        file_gid=0,
        file_uid=0,
        file_size=140401,
    )


def mock_file(file: File | FileInfo | str) -> File:
    if isinstance(file, File):
        return file
    elif isinstance(file, str):
        file_info = mock_file_info(file_name=file)
    elif isinstance(file, FileInfo):
        file_info = file
    else:
        file_info = mock_file_info(file_name=None)
    marc_data = create_marc()
    return File.from_fileinfo(file_info, io.BytesIO(marc_data.as_marc21()))


@pytest.fixture
def stub_file_info() -> FileInfo:
    return mock_file_info(file_name="foo.mrc")


class MockClient:
    def _check_dir(self, *args, **kwargs) -> None:
        pass

    def close(self) -> None:
        pass

    def fetch_file(self, file, *args, **kwargs) -> File:
        return mock_file(file=file)

    def get_file_data(self, file_name, *args, **kwargs) -> FileInfo:
        return mock_file_info(file_name=file_name)

    def is_active(self) -> bool:
        return True

    def list_file_data(self, *args, **kwargs) -> list[FileInfo]:
        return [mock_file_info(file_name=None)]

    def write_file(self, file, *args, **kwargs) -> FileInfo:
        return mock_file(file=file)


@pytest.fixture
def mock_Client(monkeypatch, mock_vendor_creds):
    def mock_check_file(*args, **kwargs):
        return False

    def mock_session(*args, **kwargs):
        return MockClient()

    def mock_sheet(*args, **kwargs):
        return {"foo": "bar"}

    monkeypatch.setattr("vendor_file_cli.validator.configure_sheet", MockCreds)
    monkeypatch.setattr("vendor_file_cli.validator.send_data_to_sheet", mock_sheet)
    monkeypatch.setenv("USERPROFILE", "test")
    monkeypatch.setattr(Client, "check_file", mock_check_file)
    monkeypatch.setattr(Client, "_Client__connect_to_server", mock_session)


@pytest.fixture
def mock_vendor_creds() -> None:
    vendors = ["NSDROP", "EASTVIEW"]
    for vendor in vendors:
        vars = {
            f"{vendor}_HOST": f"ftp.{vendor.lower()}.com",
            f"{vendor}_USER": f"{vendor.lower()}",
            f"{vendor}_PASSWORD": "bar",
            f"{vendor}_PORT": "22",
            f"{vendor}_SRC": f"{vendor.lower()}_src",
            f"{vendor}_DST": f"NSDROP/vendor_records/{vendor.lower()}",
        }
        for k, v in vars.items():
            os.environ[k] = v


@pytest.fixture
def mock_open_yaml_file(mocker):
    vendor_list = []
    vendors = ["FOO", "BAR", "BAZ", "NSDROP"]
    for vendor in vendors:
        string = (
            f"{vendor}_HOST: ftp.{vendor.lower()}.com\n"
            f"{vendor}_USER: {vendor.lower()}\n"
            f"{vendor}_PASSWORD: bar\n"
            f"{vendor}_PORT: '21'\n"
            f"{vendor}_SRC: {vendor.lower()}_src\n"
            f"{vendor}_DST: {vendor.lower()}_dst\n"
        )
        vendor_list.append(string)
    yaml_string = "\n".join(vendor_list)
    m = mocker.mock_open(read_data=yaml_string)
    mocker.patch("builtins.open", m)


@pytest.fixture
def mock_cred_config(monkeypatch, mock_open_yaml_file):
    def mock_load_vendor_creds(*args, **kwargs):
        return ["FOO", "BAR", "BAZ", "NSDROP"]

    monkeypatch.setattr(
        "vendor_file_cli.config.load_vendor_creds", mock_load_vendor_creds
    )


@pytest.fixture
def cli_runner(mocker, mock_Client, mock_cred_config):
    runner = CliRunner()
    return runner


class MockCreds:
    def __init__(self):
        self.token = "foo"

    @property
    def valid(self, *args, **kwargs):
        return True

    @property
    def expired(self, *args, **kwargs):
        return False

    @property
    def refresh_token(self, *args, **kwargs):
        return "bar"

    def refresh(self, *args, **kwargs):
        self.token = "baz"
        self.expired = False
        self.valid = True

    def to_json(self, *args, **kwargs):
        pass


@pytest.fixture
def mock_open_file(mocker):
    m = mocker.mock_open(read_data="foo")
    mocker.patch("builtins.open", m)
    return m


@pytest.fixture
def mock_sheet_config(monkeypatch):
    def get_creds(*args, **kwargs):
        return MockCreds()

    def mock_path_exists(*args, **kwargs):
        return True

    monkeypatch.setattr(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        get_creds,
    )
    monkeypatch.setattr("os.path.exists", mock_path_exists)
    monkeypatch.setenv("USERPROFILE", "test")


@pytest.fixture
def mock_sheet_config_creds_invalid(monkeypatch, mock_sheet_config, mock_open_file):
    monkeypatch.setattr(MockCreds, "valid", False)
    monkeypatch.setattr(MockCreds, "expired", True)


class MockFlow:
    def run_local_server(self, *args, **kwargs):
        return MockCreds()


@pytest.fixture
def mock_sheet_config_no_creds(monkeypatch, mock_sheet_config, mock_open_file):
    def mock_flow(*args, **kwargs):
        return MockFlow()

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
    def append(self, spreadsheetId, range, *args, **kwargs):
        self.spreadsheetId = spreadsheetId
        self.range = range
        return self

    def execute(self, *args, **kwargs):
        data = {k: v for k, v in self.__dict__.items() if not k.startswith("__")}
        return {
            "spreadsheetId": data["spreadsheetId"],
            "tableRange": data["range"],
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
def mock_sheet_resource(monkeypatch):
    def build_sheet(*args, **kwargs):
        return MockResource()

    monkeypatch.setattr("googleapiclient.discovery.build", build_sheet)
    monkeypatch.setattr("googleapiclient.discovery.build_from_document", build_sheet)


@pytest.fixture
def mock_sheet_http_error(monkeypatch, mock_sheet_resource):
    def mock_error(*args, **kwargs):
        raise HttpError(
            resp=MockError(),
            content=b"{'error': {'message':  'Bad Request'}}",
            uri="foo",
        )

    monkeypatch.setattr("googleapiclient.discovery.build", mock_error)
    monkeypatch.setattr("googleapiclient.discovery.build_from_document", mock_error)


@pytest.fixture
def mock_sheet_timeout_error(monkeypatch, mock_sheet_resource):
    def mock_error(*args, **kwargs):
        raise TimeoutError("Connection timed out")

    monkeypatch.setattr("googleapiclient.discovery.build", mock_error)
    monkeypatch.setattr("googleapiclient.discovery.build_from_document", mock_error)
