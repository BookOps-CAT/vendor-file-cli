from pymarc import Field, Subfield
import pytest
from vendor_file_cli.validator import (
    get_control_number,
    map_vendor_to_code,
    validate_single_record,
)


def test_get_control_number(stub_record):
    control_no = get_control_number(stub_record)
    assert control_no == "on1381158740"


@pytest.mark.parametrize(
    "field",
    ["020", "035", "022", "024", "010"],
)
def test_get_control_number_other_tag(stub_record, field):
    print(stub_record)
    stub_record.remove_fields("001")
    stub_record.add_ordered_field(
        Field(
            tag=field,
            indicators=[" ", " "],
            subfields=[
                Subfield(code="a", value="foo"),
            ],
        )
    )
    control_no = get_control_number(stub_record)
    assert control_no == "foo"


def test_get_control_number_call_no(stub_record):
    stub_record.remove_fields("001")
    control_no = get_control_number(stub_record)
    assert control_no == "ReCAP 23-100000"


def test_get_control_number_none(stub_record):
    stub_record.remove_fields("001", "852")
    control_no = get_control_number(stub_record)
    assert control_no == "None"


@pytest.mark.parametrize(
    "vendor, code",
    [
        ("eastview", "EVP"),
        ("leila", "LEILA"),
        ("amalivre_sasb", "AUXAM"),
        ("amalivre_lpa", "AUXAM"),
        ("amalivre_schomburg", "AUXAM"),
        ("amalivre_rl", "AUXAM"),
    ],
)
def test_map_vendor_to_code(vendor, code):
    assert map_vendor_to_code(vendor) == code


def test_validate_single_record(stub_record):
    assert validate_single_record(stub_record) == {
        "valid": True,
        "error_count": "",
        "missing_field_count": "",
        "missing_fields": "",
        "extra_field_count": "",
        "extra_fields": "",
        "invalid_field_count": "",
        "invalid_fields": "",
        "order_item_mismatches": "",
    }


def test_validate_single_record_invalid(stub_record):
    stub_record.remove_fields("960")
    assert validate_single_record(stub_record) == {
        "valid": False,
        "error_count": 1,
        "missing_field_count": 1,
        "missing_fields": ["960"],
        "extra_field_count": 0,
        "extra_fields": [],
        "invalid_field_count": 0,
        "invalid_fields": [],
        "order_item_mismatches": [],
    }
