import io
import os
from pymarc import Record, Field, Subfield
import pytest
from click.testing import CliRunner
from file_retriever.connect import Client
from file_retriever.file import File, FileInfo


def stub_marc():
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
                Subfield(
                    code="b",
                    value="subtitle /",
                ),
                Subfield(
                    code="c",
                    value="Author",
                ),
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
    return stub_marc()


@pytest.fixture
def stub_file_info() -> FileInfo:
    return mock_file_info(file_name="foo.mrc")


def mock_file(
    file_name: str | None = None,
) -> File:
    if file_name is None:
        file_name = "foo.mrc"
    marc_data = stub_marc()
    record = marc_data.as_marc21()
    return File(
        file_name=file_name,
        file_mtime=1704070800,
        file_mode=33188,
        file_atime=None,
        file_gid=0,
        file_uid=0,
        file_size=140401,
        file_stream=io.BytesIO(record),
    )


def mock_file_info(file_name: str | None = None) -> FileInfo:
    if file_name is None:
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


class MockClient:
    def _check_dir(self, *args, **kwargs) -> None:
        pass

    def close(self) -> None:
        pass

    def fetch_file(self, file, *args, **kwargs) -> File:
        if isinstance(file, str):
            return mock_file(file_name=file)
        elif isinstance(file, FileInfo):
            marc_data = stub_marc()
            return File.from_fileinfo(file, io.BytesIO(marc_data.as_marc21()))
        elif isinstance(file, File):
            return file
        else:
            return mock_file(file_name=None)

    def get_file_data(self, file_name, *args, **kwargs) -> FileInfo:
        if isinstance(file_name, str):
            return mock_file_info(file_name=file_name)
        elif isinstance(file_name, FileInfo):
            return file_name
        else:
            return mock_file_info(file_name=None)

    def is_active(self) -> bool:
        return True

    def list_file_data(self, *args, **kwargs) -> list[FileInfo]:
        return [mock_file_info(file_name=None)]

    def write_file(self, file, *args, **kwargs) -> FileInfo:
        if isinstance(file, str):
            return mock_file(file_name=file)
        elif isinstance(file, FileInfo):
            marc_data = stub_marc()
            return File.from_fileinfo(file, io.BytesIO(marc_data.as_marc21()))
        elif isinstance(file, File):
            return file
        else:
            return mock_file(file_name=None)


@pytest.fixture
def mock_Client(monkeypatch):
    def mock_check_file(*args, **kwargs):
        return False

    def mock_session(*args, **kwargs):
        return MockClient()

    monkeypatch.setattr(Client, "check_file", mock_check_file)
    monkeypatch.setattr(Client, "_Client__connect_to_server", mock_session)


@pytest.fixture
def mock_creds():
    (
        os.environ["NSDROP_HOST"],
        os.environ["NSDROP_USER"],
        os.environ["NSDROP_PASSWORD"],
        os.environ["NSDROP_PORT"],
        os.environ["NSDROP_SRC"],
    ) = ("sftp.foo.com", "NSDROP", "nsdrop", "22", "nsdrop_src")
    (
        os.environ["EASTVIEW_HOST"],
        os.environ["EASTVIEW_USER"],
        os.environ["EASTVIEW_PASSWORD"],
        os.environ["EASTVIEW_PORT"],
        os.environ["EASTVIEW_SRC"],
        os.environ["EASTVIEW_DST"],
    ) = (
        "sftp.foo.com",
        "eastview",
        "evp",
        "22",
        "eastview_src",
        "NSDROP/vendor_records/eastview",
    )


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
def mock_load_creds(monkeypatch, mock_open_yaml_file):
    def mock_path(*args, **kwargs):
        return "testdir"

    def mock_load_vendor_creds(*args, **kwargs):
        return ["FOO", "BAR", "BAZ", "NSDROP"]

    def mock_build(*args, **kwargs):
        return "foo"

    monkeypatch.setattr(
        "vendor_file_cli.config.load_vendor_creds", mock_load_vendor_creds
    )
    monkeypatch.setattr("vendor_file_cli.validator.configure_sheet", mock_build)
    monkeypatch.setattr("vendor_file_cli.validator.send_data_to_sheet", mock_build)
    monkeypatch.setenv("USERPROFILE", "test")
    monkeypatch.setattr("os.path.join", mock_path)
    monkeypatch.setattr("googleapiclient.discovery.build", mock_build)


@pytest.fixture
def cli_runner(mocker, mock_Client, mock_load_creds):
    runner = CliRunner()
    return runner
