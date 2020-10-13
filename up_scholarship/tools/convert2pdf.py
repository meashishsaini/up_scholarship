import pdfkit
from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers.constants import CommonData, FormKeys
from up_scholarship.providers import utilities as utl
from up_scholarship.providers.file_name import FileName
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 9 - 85
# 10 - 85
options_9_10 = {
	'encoding': 'utf-8',
	'margin-bottom': '25',
	'zoom': '1.1',
	'page-size': 'A4'}
options_11 = {
	'encoding': 'utf-8',
	'margin-top': '5',
	'margin-bottom': '14',
	'page-size': 'A4',
	'zoom': '0.9'}
options_12 = {
	'encoding': 'utf-8',
	'margin-top': '5',
	'margin-bottom': '20',
	'page-size': 'A4',
	'zoom': '0.9'}
# win32api.ShellExecute(0, "print", "out.pdf", None,  ".",  0)
def convert2pdf():
	cd = CommonData()
	students = StudentFile().read_file(cd.students_in_file, cd.file_in_type)
	filename = FileName("finalsubmit")
	for student in students:
		if student[FormKeys.skip()] == 'Y' or student[FormKeys.final_submitted()] == 'N':
			continue
		# if student[utl.keys.aadhaar_no()] != '703042679780':
		# 	continue
		filename_in = filename.get(student, "html", student[FormKeys.reg_year()], extra="/finalprint")
		filename_out = filename.get(student, "pdf", student[FormKeys.reg_year()], extra="/pdf/finalprint")
		# filename_in = 'out/final/' + utl.get_save_file(student) + '/finalprint.html'
		# filename_out = 'out/final/' + utl.get_save_file(student) + '/pdf/finalprint.pdf'
		if utl.check_if_file_exists(filename_out):
			continue
		os.makedirs(os.path.dirname(filename_out), exist_ok=True)
		if student[FormKeys.std()] == '9' or student[FormKeys.std()] == '10':
			options = options_9_10
		elif student[FormKeys.std()] == '11':
			options = options_11
		else:
			options = options_12
		out_string = f"{student[FormKeys.name()]}.{student[FormKeys.father_name()]}.{student[FormKeys.mother_name()]} of std {student[FormKeys.std()]}"
		logger.info("Processing: %s", out_string)
		logger.info("Input filename: %s", filename_in)
		logger.info("Output filename: %s", filename_out)
		print("Processing:", out_string)
		try:
			pdfkit.from_file(filename_in, filename_out, options=options)
			print("Processing success")
		except IOError as err:
			logger.error(err)
			print("Processing failed:", err)
		
		
