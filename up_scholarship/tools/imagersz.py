import sys
import os
from pathlib import Path
import subprocess


def resize(filename: str, image_size: int):
	if Path(filename).is_file():
		statinfo = os.stat(filename)
		if statinfo.st_size > image_size * 1024:
			subprocess.call(["magick", filename, "-define", "jpeg:extent=" + str(image_size) + "kb", filename])
