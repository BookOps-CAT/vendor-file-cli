import os
import click
from vendor_file_cli.commands import get_vendor_files, validate_files
from vendor_file_cli.utils import (
    load_vendor_creds,
    configure_logger,
    create_logger_dict,
)


@click.group
def vendor_file_cli() -> None:
    """CLI for retrieving files from vendor FTP/SFTP servers."""
    logger_dict = create_logger_dict()
    configure_logger(logger_dict)
    pass


@vendor_file_cli.command(
    "all-vendor-files",
    short_help="Retrieve and validate files that are not in NSDROP.",
)
def get_all_vendor_files() -> None:
    """
    Retrieve files from vendor server not present in vendor's NSDROP directory. Creates
    list of files on vendor server and list of files in NSDROP directory. Copies files
    from vendor server to NSDROP directory if they are not already present. Validates
    files for Eastview, Leila, and Amalivre (SASB) before copying them to NSDROP and
    writes output of validation to google sheet. Files are copied to
    NSDROP/vendor_records/{vendor_name}.

    Args:
        None

    Returns:
        None

    """
    vendor_list = load_vendor_creds(
        os.path.join(os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml")
    )
    get_vendor_files(vendors=vendor_list)


@vendor_file_cli.command("available-vendors", short_help="List all configured vendors.")
def get_available_vendors() -> None:
    """List all configured vendors."""
    vendor_list = load_vendor_creds(
        os.path.join(os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml")
    )
    click.echo(f"Available vendors: {vendor_list}")


@vendor_file_cli.command(
    "validate-file",
    short_help="Validate vendor file on NSDROP.",
)
@click.option(
    "--vendor",
    "-v",
    "vendor",
    help="Which vendor to validate files for.",
)
@click.option(
    "--file",
    "-f",
    "file",
    help="The file you would like to validate.",
)
def validate_vendor_files(vendor: str, file: str) -> None:
    """
    Validate files for a specific vendor.

    Args:
        vendor:
            name of vendor to validate files for. files will be validated for
            the specified vendor
        file:
            name of file to validate
    Returns:
        None
    """
    load_vendor_creds(
        os.path.join(os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml")
    )
    validate_files(vendor=vendor, files=[file])


@vendor_file_cli.command(
    "vendor-files",
    short_help="Retrieve files from remote server based on timedelta.",
)
@click.option(
    "--vendor",
    "-v",
    "vendor",
    type=str,
    multiple=True,
    help="Vendor to retrieve files for.",
)
@click.option(
    "--days",
    "-d",
    "days",
    default=0,
    type=int,
    help="How many days back to retrieve files.",
)
@click.option(
    "--hours",
    "-h",
    "hours",
    default=0,
    type=int,
    help="How many hours back to retrieve files.",
)
def get_recent_vendor_files(vendor: str, days: int, hours: int) -> None:
    """
    Retrieve files from remote server for specified vendor(s).

    Args:
        vendor:
            name of vendor to retrieve files from. if 'all' then all vendors
            listed in config file will be included, otherwise multiple values
            can be passed and each will be added to a list. files will be
            retrieved for each vendor in the list
        days:
            number of days to go back and retrieve files from
        hours:
            number of hours to go back and retrieve files from

    Returns:
        None

    """
    all_available_vendors = load_vendor_creds(
        os.path.join(os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml")
    )
    if "all" in vendor:
        vendor_list = all_available_vendors
    else:
        vendor_list = [i.upper() for i in vendor]
    get_vendor_files(vendors=vendor_list, days=days, hours=hours)


def main():
    vendor_file_cli()
