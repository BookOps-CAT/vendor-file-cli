import logging
import logging.config
import os
import click
from file_retriever.utils import logger_config
from vendor_file_cli.commands import load_vendor_creds, get_recent_files


logger = logging.getLogger("file_retriever")
config = logger_config()
logging.config.dictConfig(config)


@click.group
def vendor_file_cli() -> None:
    """
    CLI for retrieving files from vendor FTP/SFTP servers.
    """
    pass


@vendor_file_cli.command(
    "vendor-files", short_help="Retrieve files from remote server."
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
def get_files(vendor: str, days: int, hours: int, minutes: int) -> None:
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
    get_recent_files(vendors=vendor_list, days=days, hours=hours, minutes=minutes)


@vendor_file_cli.command(
    "daily-vendor-files", short_help="Retrieve previous day's files from remote server."
)
def get_files_today() -> None:
    """
    Retrieve files updated within last day from remote server for all vendor(s).

    Args:
        ctx: click context object that contains a list of vendor names

    """
    vendor_list = load_vendor_creds(
        os.path.join(os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml")
    )
    click.echo(f"Available vendors: {vendor_list}")
    get_recent_files(vendors=vendor_list, days=1)


@vendor_file_cli.command("available-vendors", short_help="List all configured vendors.")
def list_vendors() -> None:
    """
    List all configured vendors.

    Args:
        ctx: click context object that contains a list of vendor names

    """
    vendor_list = load_vendor_creds(
        os.path.join(os.environ["USERPROFILE"], ".cred/.sftp/connections.yaml")
    )
    click.echo(f"Available vendors: {vendor_list}")


def main():
    vendor_file_cli()
