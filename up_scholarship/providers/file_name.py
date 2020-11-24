from up_scholarship.providers import utilities as utl

class FileName:
	def __init__(self, name: str):
		self.name = name

	def get(self, student, extension: str, year: str, tried=0, extra=None, is_debug=False) -> str:
		filename = f"up_scholarship/out/{year}/"
		if is_debug:
			filename = filename + "debug/"
		if self.name:
			filename = filename + self.name + "/"
		else:
			filename = filename + "others/"
		filename = filename + utl.get_save_file(student, tried)
		if extra:
			filename = filename + extra
		if extension:
			filename = filename + "." + extension
		return filename
