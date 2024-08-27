import io
import pytest
from click.testing import CliRunner
from file_retriever.connect import Client
from file_retriever.file import File, FileInfo


def mock_file_info() -> FileInfo:
    return FileInfo(
        file_name="foo.mrc",
        file_mtime=1704070800,
        file_mode=33188,
        file_atime=None,
        file_gid=0,
        file_uid=0,
        file_size=140401,
    )


class MockClient:
    def _check_dir(self, *args, **kwargs) -> None:
        pass

    def close(self) -> None:
        pass

    def fetch_file(self, *args, **kwargs) -> File:
        return File.from_fileinfo(file=mock_file_info(), file_stream=io.BytesIO(b"foo"))

    def get_file_data(self, *args, **kwargs) -> FileInfo:
        return mock_file_info()

    def is_active(self) -> bool:
        return True

    def list_file_data(self, *args, **kwargs) -> list[FileInfo]:
        return [mock_file_info()]

    def write_file(self, *args, **kwargs) -> FileInfo:
        return mock_file_info()


@pytest.fixture
def mock_Client(monkeypatch):
    def mock_check_file(*args, **kwargs):
        return False

    def mock_session(*args, **kwargs):
        return MockClient()

    monkeypatch.setattr(Client, "check_file", mock_check_file)
    monkeypatch.setattr(Client, "_Client__connect_to_server", mock_session)


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
def mock_load_vendor_creds(monkeypatch, mock_open_yaml_file):
    def mock_path(*args, **kwargs):
        return "testdir"

    def mock_load_vendor_creds(*args, **kwargs):
        return ["FOO", "BAR", "BAZ", "NSDROP"]

    monkeypatch.setattr(
        "vendor_file_cli.commands.load_vendor_creds", mock_load_vendor_creds
    )
    monkeypatch.setenv("USERPROFILE", "test")
    monkeypatch.setattr("os.path.join", mock_path)


@pytest.fixture
def cli_runner(mocker, mock_Client, mock_load_vendor_creds):
    runner = CliRunner()
    return runner
