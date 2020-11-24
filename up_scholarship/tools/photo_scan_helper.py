from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers.constants import CommonData, FormKeys
from scan_helper.scan import get_scanned_image
from scan_helper.align_faces import align_face
from scan_helper.resize import resize
from datetime import datetime
from cv2 import cv2
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
						except Exception as err:
							logger.error(err)
							print("Unable to scan image.")
						# align face in the image
						else:
							try:
								images = align_face(show=False, pil_image=image,
								desired_height=540,
								desired_width=420)
								assert len(images) != 0
							except Exception as err:
								logger.error(err)
								print("Unable to find faces.")
							else:
								try:
									for i in range(len(images)):
										cv_image = cv2.cvtColor(np.array(images[i]), cv2.COLOR_RGB2BGR)
										cv2.imshow(f"{student[FormKeys.name()]} (Choice {i})", cv_image)
									cv2.waitKey(0)
									choice = input(f"Enter your choice? <{0}-{len(images)-1}> ")
									choice = int(choice)
									if choice < 0 or choice > len(images):
										choice = 0
									image = images[choice]
									
									image.save(filename, "JPEG")

									# resize image
									abs_filename = os.path.abspath(filename)
									metadata = os.stat(abs_filename)
									if metadata.st_size > file_max_size * 1000:
										resize(abs_filename, file_max_size)
								except Exception as e:
									logger.error(e)
									print("Unable to save image file.")
						input("Press Enter to continue...")
			if not found:
				print("Unable to find UID.")
				input("Press Enter to continue...")	
		else:
			print("Bye bye")
			break
