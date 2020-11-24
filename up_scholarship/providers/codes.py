import json
import logging

class CodeFileReader:
	_codes_map = {}

	def __init__(self, file_name: str):
		try:
			f = open(file_name, "r", encoding="utf-8")
		except IOError:
			logging.getLogger().error("Unable to read file: " + file_name)
			raise Exception("CodeFileReader class initialization failed.")
		else:
			with f:
				self._codes_map = json.load(f)

	def get_code(self, str1: str, str2="") -> str:
		if len(str2) > 0:
			bank = self._codes_map.get(str1.lower())
			if bank:
				return bank.get(str2.lower(), '')
			else:
				raise Exception("Unable to find bank and branch.")
		else:
			return self._codes_map.get(str1.lower(), '')
