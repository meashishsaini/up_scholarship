import pyperclip
from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers.constants import CommonData, FormKeys
import os
from pathlib import Path


def name_string():
	cd = CommonData()
	students = StudentFile().read_file(cd.students_in_file, cd.file_in_type)
	while True:
		aadhaar_no = input('Please enter aadhaar number. ')
		os.system('cls')
		if len(aadhaar_no) == 12:
			for student in students:
				if aadhaar_no == student[FormKeys.aadhaar_no()]:
					filename = 'data/photos/by_UID/' + student[FormKeys.std()] + '/' + student[
						FormKeys.aadhaar_no()] + '.jpg'
					if Path(filename).is_file():
						print("Photo already exists.")
					data = student[FormKeys.name()] + '.' + student[FormKeys.father_name()] + '.' + student[
						FormKeys.mother_name()]
					# Copy aadhaar number to clipboard
					pyperclip.copy(aadhaar_no)
					print(data + ' of std ' + student[FormKeys.std()] + ' skip: ' + student[FormKeys.skip()])
		else:
			print("Bye bye")
			break
