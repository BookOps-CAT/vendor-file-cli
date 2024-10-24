import logging
import logging.config
import os
import yaml

logger = logging.getLogger(__name__)


def configure_logger(logger_dict: dict) -> None:
    logging.config.dictConfig(logger_dict)
    loggers = [i for i in logger_dict["loggers"].keys()]
    for logger in loggers:
        logging.getLogger(f"{logger}")


def create_logger_dict() -> dict:
    loggly_token = os.environ.get("LOGGLY_TOKEN")
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "basic": {
                "format": "%(app_name)s-%(asctime)s-%(name)s-%(lineno)d-%(levelname)s-%(message)s",  # noqa: E501
                "defaults": {"app_name": "vendor_file_cli"},
            },
            "json": {
                "format": '{"app_name": "%(app_name)s", "asctime": "%(asctime)s", "name": "%(name)s", "lineno":"%(lineno)d", "levelname": "%(levelname)s", "message": "%(message)s"}'  # noqa: E501
            },
        },
        "handlers": {
            "stream": {
                "class": "logging.StreamHandler",
                "formatter": "basic",
                "level": "DEBUG",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "basic",
                "level": "DEBUG",
                "filename": "vendor_file_cli.log",
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
            },
            "loggly": {
                "class": "loggly.handlers.HTTPSHandler",
                "formatter": "json",
                "level": "INFO",
                "url": f"https://logs-01.loggly.com/inputs/{loggly_token}/tag/python",
            },
        },
        "loggers": {
            "file_retriever": {
                "handlers": ["stream", "file", "loggly"],
                "level": "DEBUG",
                "propagate": True,
            },
            "file_retriever.vendor_file_cli": {
                "handlers": ["stream", "file", "loggly"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
    }


def load_vendor_creds(config_path: str) -> list[str]:
    """
    Read config file with credentials and set creds as environment variables.
    Returns a list of vendors whose FTP/SFTP credentials are stored in the
    config file and have been added to env vars. NSDROP is excluded from this list.

    Args:
        config_path (str): Path to the yaml file with credendtials.

    Returns:
        list of names of servers (eg. EASTVIEW, LEILA) whose credentials are
        stored in the config file and have been added to env vars
    """
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
        if config is None:
            raise ValueError("No credentials found in config file.")
        vendor_list = [
            i.split("_HOST")[0]
            for i in config.keys()
            if i.endswith("_HOST") and "NSDROP" not in i
        ]
        for k, v in config.items():
            os.environ[str(k)] = str(v)
        for vendor in vendor_list:
            os.environ[f"{vendor}_DST"] = f"NSDROP/vendor_records/{vendor.lower()}"
        return vendor_list
