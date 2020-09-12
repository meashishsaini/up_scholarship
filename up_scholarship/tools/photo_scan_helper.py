from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers.constants import CommonData, FormKeys
from up_scholarship.tools.scan_photo import get_scanned_image
from up_scholarship.tools.straightening2 import straighten_face
from up_scholarship.tools.imagersz import resize
from datetime import datetime
import cv2
import os
from pathlib import Path
import logging
import numpy as np


logger = logging.getLogger(__name__)
file_max_size = 20  # KB


def scan_photos():
	cd = CommonData()
	students = StudentFile().read_file(cd.students_in_file, cd.file_in_type)
	while True:
		found = False
		os.system('cls')
		UID_no = input('Please enter UID number. ')
		if len(UID_no) == 12:
			for student in students:
				if UID_no == student[FormKeys.aadhaar_no()]:
					found = True
					filename = cd.data_dir + 'photos/by_UID/' + str(datetime.today().year) + '/' + \
							   student[FormKeys.std()] + '/' + student[FormKeys.aadhaar_no()] + '.jpg'
					replace = "y"
					print("Photo for %s. Father name: %s of std %s" % (
						student[FormKeys.name()], student[FormKeys.father_name()], student[FormKeys.std()]))
					os.makedirs(os.path.dirname(filename), exist_ok=True)
					if Path(filename).is_file():
						print("Photo already exists.")
						cv2.imshow(student[FormKeys.name()], cv2.imread(filename, cv2.IMREAD_COLOR))
						cv2.waitKey(0)
						replace = input("Replace the photo. (y/n) ")
					if replace == "y":
						input("Press Enter to continue...")
						# get scanned image from our function
						try:
							os.makedirs(os.path.dirname(filename), exist_ok=True)
							image = get_scanned_image()
							image = straighten_face(image)
							# get cropped image from our function
							# image = crop_image(image)
							image.save(filename, "JPEG")
							img = cv2.imread(filename, cv2.IMREAD_COLOR)
							cv2.imshow(student[FormKeys.name()],img)
							cv2.waitKey()
							# Resize image file if it is greater than max size
							abs_filename = os.path.abspath(filename)
							metadata = os.stat(abs_filename)
							if metadata.st_size > file_max_size * 1000:
								resize(abs_filename, file_max_size)
						except Exception as e:
							logger.error(e)
						except:
							logger.error("Unable to find a face.")
			if not found:
				print("Unable to find UID.")
				input("Press Enter to continue...")	
		else:
			print("Bye bye")
			break
