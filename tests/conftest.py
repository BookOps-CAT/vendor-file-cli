import io
import logging
import os
from typing import Dict
import yaml
import pytest
from file_retriever.connect import Client
from file_retriever._clients import _ftpClient, _sftpClient
from file_retriever.file import File, FileInfo

logger = logging.getLogger("file_retriever")


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


class Mock_BaseClient:
    def __init__(self):
        pass

    def close(self):
        pass


class MockFile:
    def __init__(self):
        self.file_name = "foo.mrc"
        self.file_mtime = 1704070800
        self.file_mode = 33188
        self.file_atime = None
        self.file_gid = 0
        self.file_uid = 0
        self.file_size = 140401
        self.file_stream = io.BytesIO(b"foo")

    def file_info_obj(self) -> FileInfo:
        return FileInfo(
            file_name=self.file_name,
            file_mtime=self.file_mtime,
            file_mode=self.file_mode,
            file_atime=self.file_atime,
            file_gid=self.file_gid,
            file_uid=self.file_uid,
            file_size=self.file_size,
        )

    def file_obj(self) -> File:
        return File(
            file_name=self.file_name,
            file_mtime=self.file_mtime,
            file_mode=self.file_mode,
            file_atime=self.file_atime,
            file_gid=self.file_gid,
            file_uid=self.file_uid,
            file_size=self.file_size,
            file_stream=self.file_stream,
        )


@pytest.fixture
def mock_Client(monkeypatch):
    def mock_connection_check(*args, **kwargs):
        return True

    def mock_file_exists(*args, **kwargs):
        return False

    def mock_file_info(*args, **kwargs):
        return MockFile().file_info_obj()

    def mock_file_info_list(*args, **kwargs):
        return [MockFile().file_info_obj()]

    def mock_file(*args, **kwargs):
        return MockFile().file_obj()

    def mock_connection(*args, **kwargs):
        return Mock_BaseClient()

    monkeypatch.setattr(Client, "file_exists", mock_file_exists)
    monkeypatch.setattr(_ftpClient, "is_active", mock_connection_check)
    monkeypatch.setattr(_sftpClient, "is_active", mock_connection_check)
    monkeypatch.setattr(_ftpClient, "get_file_data", mock_file_info)
    monkeypatch.setattr(_sftpClient, "get_file_data", mock_file_info)
    monkeypatch.setattr(_ftpClient, "list_file_data", mock_file_info_list)
    monkeypatch.setattr(_sftpClient, "list_file_data", mock_file_info_list)
    monkeypatch.setattr(_ftpClient, "fetch_file", mock_file)
    monkeypatch.setattr(_sftpClient, "fetch_file", mock_file)
    monkeypatch.setattr(_ftpClient, "write_file", mock_file_info)
    monkeypatch.setattr(_sftpClient, "write_file", mock_file_info)
    monkeypatch.setattr(_ftpClient, "_connect_to_server", mock_connection)
    monkeypatch.setattr(_sftpClient, "_connect_to_server", mock_connection)


@pytest.fixture
def stub_creds() -> Dict[str, str]:
    return {
        "host": "ftp.testvendor.com",
        "username": "test_username",
        "password": "test_password",
    }


@pytest.fixture
def live_creds() -> None:
    with open(
        os.path.join(os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml")
    ) as cred_file:
        data = yaml.safe_load(cred_file)
        for k, v in data.items():
            os.environ[k] = v
