import logging
import logging.handlers
import os
import yaml

logger = logging.getLogger("vendor_file_cli")


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
            os.environ[k] = v
        for vendor in vendor_list:
            os.environ[f"{vendor}_DST"] = f"NSDROP/vendor_records/{vendor.lower()}"
        return vendor_list


def logger_config(app_logger: logging.Logger) -> None:
    """
    Create and return dict for logger configuration.
    """
    root_logger = logging.getLogger("file_retriever")
    root_logger.setLevel(logging.DEBUG)
    app_logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    file_handler = logging.handlers.RotatingFileHandler(
        filename="vendor_file_cli.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf8",
    )
    formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s")

    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    app_logger.addHandler(stream_handler)
    app_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
