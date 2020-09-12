import numpy as np
import cv2
import logging
from PIL import Image
from up_scholarship.tools.scan_photo import get_scanned_image
import math

logger = logging.getLogger(__name__)


def straighten_face(image) -> Image:
	# load opencv face detect files
	facedata = "haarcascade_frontalface_alt.xml"
	face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + facedata)

	eyedata = "haarcascade_eye.xml"
	eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + eyedata)

	# Convert image to cv2 format form PIL image from our scan image function
	img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
	# orig_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

	minisize = (img.shape[1], img.shape[0])
	miniframe = cv2.resize(img, minisize)

	# detect faces
	faces = face_cascade.detectMultiScale(miniframe)

	logger.info("%d face(s) found." % len(faces))
	# assert if we have a face
	assert (len(faces) > 0)

	# get first page of the list
	face = faces[0]

	# get coordinates and width and height of the face
	x, y, w, h = [v for v in face]

	# get eyes coordinates using face region
	eyes = eye_cascade.detectMultiScale(img[y:y + h, x:x + w])

	rows, cols = img.shape[:2]

	# Used (y2 - y1)/(x2-x1) for calculating angle
	angle = math.atan2(eyes[1][1] - eyes[0][1], eyes[1][0] - eyes[0][0])

	# Rotate image
	M = cv2.getRotationMatrix2D((cols / 2, rows / 2), math.degrees(angle), 1)
	img_rotated = cv2.warpAffine(img, M, (cols, rows))
	img_rotated = cv2.cvtColor(img_rotated, cv2.COLOR_BGR2RGB)

	return Image.fromarray(img_rotated)


if __name__ == "__main__":
	image = get_scanned_image()
	cropped_image = straighten_face(image)
	cropped_image.save("cropped.jpg", "JPEG")