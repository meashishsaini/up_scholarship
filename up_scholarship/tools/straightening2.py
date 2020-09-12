import sys

import dlib
import cv2
from imutils.face_utils import FaceAligner
from PIL import Image
from up_scholarship.tools.scan_photo import get_scanned_image
import numpy as np
import logging

logger = logging.getLogger(__name__)


def straighten_face(image) -> Image:
	predictor_path = "up_scholarship/tools/face_model/shape_predictor_5_face_landmarks.dat"
	# Load all the models we need: a detector to find the faces, a shape predictor
	# to find face landmarks so we can precisely localize the face
	detector = dlib.get_frontal_face_detector()
	predictor = dlib.shape_predictor(predictor_path)
	cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

	gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

	fa = FaceAligner(predictor, desiredFaceWidth=480, desiredFaceHeight=600)
	# Ask the detector to find the bounding boxes of each face. The 1 in the
	# second argument indicates that we should up sample the image 1 time. This
	# will make everything bigger and allow us to detect more faces.
	rectangles = detector(gray, 1)
	print("%d face(s) found." % len(rectangles))
	logger.info("%d face(s) found." % len(rectangles))
	# assert if we have a face
	assert (len(rectangles) > 0)

	rect = rectangles[0]
	# extract the ROI of the *original* face, then align the face
	# using facial landmarks
	faceAligned = fa.align(cv_image, gray, rect)
	faceAligned = cv2.cvtColor(faceAligned, cv2.COLOR_BGR2RGB)
	return Image.fromarray(faceAligned)


if __name__ == "__main__":
	image = get_scanned_image()
	cropped_image = straighten_face(image)
	cropped_image.save("aligned_cropped.jpg", "JPEG")
