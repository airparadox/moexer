import logging
import os
from datetime import datetime
from dotenv import load_dotenv


def setup_logging() -> None:
    """Configure logging to write to file and console.

    The log file path can be configured via the ``LOG_FILE`` environment variable.
    By default logs are written to ``.log/`` directory with name ``stYYYY-MM-DD.log``.
    """
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path=dotenv_path)

    log_dir = os.getenv("LOG_FILE", ".log/")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"st{datetime.now().date()}.log")

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
