import io
import logging
import logging.config
from typing import List
import pytest
from click.testing import CliRunner
from file_retriever.connect import Client
from file_retriever.file import File, FileInfo
from file_retriever.utils import logger_config

logger = logging.getLogger("file_retriever")
config = logger_config()
logging.config.dictConfig(config)


@pytest.fixture
def mock_yaml() -> str:
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
    return yaml_string


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

    def list_file_data(self, *args, **kwargs) -> List[FileInfo]:
        return [mock_file_info()]

    def write_file(self, *args, **kwargs) -> FileInfo:
        return mock_file_info()


@pytest.fixture
def mock_Client(monkeypatch):
    def mock_file_exists(*args, **kwargs):
        return False

    def mock_session(*args, **kwargs):
        return MockClient()

    monkeypatch.setattr(Client, "file_exists", mock_file_exists)
    monkeypatch.setattr(Client, "_Client__connect_to_server", mock_session)


@pytest.fixture
def cli_runner(mocker, mock_Client, mock_yaml):
    m = mocker.mock_open(read_data=mock_yaml)
    mocker.patch("builtins.open", m)
    runner = CliRunner()
    return runner
