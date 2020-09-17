from up_scholarship.providers.constants import WorkType
from up_scholarship.providers import utilities as utl


class FileName:
	def __init__(self, work_type: WorkType):
		self.work_type = work_type

	def get(self, student, extension: str, year: str, extra=None, is_debug=False) -> str:
		filename = 'up_scholarship/out/%s/' % year
		if is_debug:
			filename = filename + 'debug/'
		if self.work_type == WorkType.register:
			filename = filename + 'registration/'
		elif self.work_type == WorkType.fill_data:
			filename = filename + 'filldata/'
		elif self.work_type == WorkType.photo:
			filename = filename + 'photo/'
		elif self.work_type == WorkType.submit_check:
			filename = filename + 'check/'
		elif self.work_type == WorkType.renew:
			filename = filename + 'renew/'
		elif self.work_type == WorkType.final_submit:
			filename = filename + 'final/'
		elif self.work_type == WorkType.receive:
			filename = filename + 'verify/'
		elif self.work_type == WorkType.receive:
			filename = filename + 'verify/'
		elif self.work_type == WorkType.forward:
			filename = filename + 'forward/'
		elif self.work_type == WorkType.aadhaar_auth:
			filename = filename + 'aadhaar/'
		filename = filename + utl.get_save_file(student)
		if extra:
			filename = filename + extra
		if extension:
			filename = filename + "." + extension
		return filename
