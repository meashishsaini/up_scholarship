from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers.constants import CommonData, FormKeys, StdCategory
from up_scholarship.providers import utilities as utl
from up_scholarship.providers.file_name import FileName

import os
import logging
from win32 import win32api

logger = logging.getLogger(__name__)


# win32api.ShellExecute(0, "print", "out.pdf", None,  ".",  0)
def print_final():
	cd = CommonData()
	students = StudentFile().read_file(cd.students_in_file, cd.file_in_type)
	filename = FileName("finalsubmit")

	no_of_students = len(students)
	x = 0
	while True:
		x += 1
		if x >= no_of_students:
			break
		student = students[x]
		# if utl.get_std_category(student[FormKeys.std()]) == StdCategory.pre:
		# 	continue
		os.system('cls')
		data = student[FormKeys.name()] + '.' + student[FormKeys.father_name()] + '.' + student[FormKeys.mother_name()]
		print(data + ' of std ' + student[FormKeys.std()])
		if student[FormKeys.final_submitted()] == 'N' or student[FormKeys.final_printed()] == 'Y':
			print('Skipping - ' + data + ' Skip: ' + student[FormKeys.skip()] + ' Final Submitted: ' +
									student[FormKeys.final_submitted()] + ' Printed: ' + student[FormKeys.final_printed()])
			continue
		opt = input(" p - to print student's final page \n s - to skip the student \n e - exit\n")
		if opt == 'p':
			filename_in = filename.get(student, "pdf", student[FormKeys.reg_year()], extra="/pdf/finalprint")
			filename_in = os.path.abspath(filename_in)
			logger.info("Printing file: %s" % filename_in)
			hinstance = -1
			file_printed = False
			if utl.check_if_file_exists(filename_in):
				hinstance = win32api.ShellExecute(0, "print", filename_in, None, ".", 0)
				if hinstance <= 32:
					status = 'Unable to print the student final page. HINSTANCE: ' + str(hinstance)
					file_printed = False
				else:
					status = 'Print command succeeded.'
					file_printed = True
			else:
				status = filename_in + ' doesn\'t exist.'
				file_printed = False
			if file_printed:
				opt = input(" Enter 't' if print succeed else 'f' or 'r' to retry\n")
				if opt == 't':
					student[FormKeys.final_printed()] = 'Y'
				elif opt == 'r':
					print("Retrying print...")
					x -= 1
				else:
					status = 'Marked as not printed'
					file_printed = False
			logger.info(status)
			print(status)
			student[FormKeys.status()] = status
			if not file_printed:
				input("Press enter key to continue...")
			else:
				students[x] = student
		elif opt == 's':
			pass
		else:
			break

	utl.copy_file(cd.students_in_file, cd.students_old_file)
	StudentFile().write_file(students, cd.students_in_file, cd.students_out_file, cd.file_out_type)
