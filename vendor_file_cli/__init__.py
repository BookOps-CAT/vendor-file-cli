import logging
import logging.config
import os
import click
from vendor_file_cli.commands import get_vendor_files, validate_files
from vendor_file_cli.config import load_vendor_creds, logger_config


@click.group
def vendor_file_cli() -> None:
    """CLI for retrieving files from vendor FTP/SFTP servers."""
    logger = logging.getLogger("vendor_file_cli")
    logger_config(logger)
    pass


@vendor_file_cli.command(
    "all-vendor-files",
    short_help="Retrieve and validate files that are not in NSDROP.",
)
def get_all_vendor_files() -> None:
    """Retrieve files from vendor server not present in vendor's NSDROP directory."""
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
@click.option(
    "--minutes",
    "-m",
    "minutes",
    default=0,
    type=int,
    help="How many minutes back to retrieve files.",
)
def get_recent_vendor_files(vendor: str, days: int, hours: int, minutes: int) -> None:
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
        minutes:
            number of minutes to go back and retrieve files from

    """
    all_available_vendors = load_vendor_creds(
        os.path.join(os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml")
    )
    if "all" in vendor:
        vendor_list = all_available_vendors
    else:
        vendor_list = [i.upper() for i in vendor]
    get_vendor_files(vendors=vendor_list, days=days, hours=hours, minutes=minutes)


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
def validate_vendor_files(vendor: str) -> None:
    if not os.getenv("GITHUB_ACTIONS"):
        load_vendor_creds(
            os.path.join(os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml")
        )
    validate_files(vendor=vendor, files=None)


def main():
    vendor_file_cli()
