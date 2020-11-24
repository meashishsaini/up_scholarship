import logging
from logging.handlers import RotatingFileHandler
import os

filename = os.path.dirname(__file__) + "/logs.log"

# get handler
rotating_file_handler = RotatingFileHandler(filename=filename, mode="w", encoding="utf-8")
rotating_file_handler.setLevel(logging.INFO)
# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# add formatter to handler
rotating_file_handler.setFormatter(formatter)

# get root logger
root = logging.getLogger()
root.setLevel(logging.DEBUG)

# add handler to logger
root.addHandler(rotating_file_handler)

from dotenv import load_dotenv
load_dotenv()