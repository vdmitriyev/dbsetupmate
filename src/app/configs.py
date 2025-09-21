import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SERVER_TITLE = "dbmate"

LOGS_DIR = ".logs"
CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"
CONFIGS_DIR = ".configs"

LOGS_PATH = os.path.join(Path(__file__).resolve().parent.parent, LOGS_DIR)
CONFIGS_PATH = os.path.join(Path(__file__).resolve().parent.parent, CONFIGS_DIR)
CERT_PATH = os.path.join(CONFIGS_PATH, CERT_FILE)
KEY_PATH = os.path.join(CONFIGS_PATH, KEY_FILE)

APP_LOG_LEVEL = os.environ.get("APP_LOG_LEVEL", "INFO").upper()

# Configure logging
logging.basicConfig(
    level=APP_LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOGS_PATH, "server.log")),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("dbmate")


def ensure_directory_exists(path: str):
    """
    Ensures a directory exists using the os module.
    Creates the directory if it doesn't exist.
    Handles creation of parent directories if they don't exist.
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logger.info(f"Directory has been created: {path}")
    except OSError as e:
        logger.error(f"Error creating directory '{path}': {e}")


def load_envs():
    """Loads environmental variables from the file"""
    from datetime import datetime

    env_file = os.environ.get("ENV_FILE_NAME") or None
    basedir = os.path.abspath(os.path.dirname(__file__))

    def load_from_default_env():
        DEFAULT_ENV_FILE_NAME = ".env"
        logger.info(f"trying to load default `.env` file: {DEFAULT_ENV_FILE_NAME}")
        load_dotenv(os.path.join(basedir, DEFAULT_ENV_FILE_NAME), override=True)
        print(os.path.join(basedir, DEFAULT_ENV_FILE_NAME))

    if env_file is not None:
        print(os.path.join(basedir, env_file))
        if os.path.exists(env_file):
            logger.info(f"loading environmental variables from the file: {env_file}")
            load_dotenv(env_file, override=True)
        elif os.path.exists(os.path.join(basedir, env_file)):

            logger.info(f"loading environmental variables from the file: {env_file}")
            load_dotenv(env_file, override=True)
        else:
            logger.info(f"provided `.env` file does not exist: {env_file}")
            load_from_default_env()
    else:
        logger.info(f"custom `.env` file name has not been provided")
        load_from_default_env()


def silence_verbose_logging():
    logging.debug("Silence verbose logging output")
    # Silent the logging of urllib3
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)


def validate_important_envs():
    pass


validate_important_envs()
ensure_directory_exists(CONFIGS_PATH)
ensure_directory_exists(LOGS_PATH)
silence_verbose_logging()
