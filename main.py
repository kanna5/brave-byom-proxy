import logging

import dotenv

from app import app
from config import config

__all__ = ["app"]

dotenv.load_dotenv()
config.load_from_env()
logging.basicConfig(level=logging.INFO)
