import numpy as np
import cv2
import logging
from PIL import Image
from up_scholarship.tools.scan_photo import get_scanned_image
from up_scholarship.tools.straightening import straighten_face

logger = logging.getLogger(__name__)


def crop_image(image) -> Image:
	# load opencv face detect file
	facedata = "haarcascade_frontalface_alt.xml"
	cascade = cv2.CascadeClassifier(cv2.data.haarcascades + facedata)

	# Convert image to cv2 format form PIL image from our scan image function
	img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

	minisize = (img.shape[1], img.shape[0])
	miniframe = cv2.resize(img, minisize)

	# detect faces
	faces = cascade.detectMultiScale(miniframe)

	logger.info("%d face(s) found." % len(faces))
	# assert if we have a face
	assert (len(faces) > 0)

	# get first page of the list
	face = faces[0]

	# add some padding up and bottom of the face
	width_padding = 80
	height_padding_bottom = 120
	height_padding_top = 70

	# get coordinates and width and height of the face
	x, y, w, h = [v for v in face]
	sub_face = img[y - height_padding_top:y + h + height_padding_bottom, x - width_padding:x + w + width_padding]

	sub_face = cv2.cvtColor(sub_face, cv2.COLOR_BGR2RGB)
	return Image.fromarray(sub_face)


if __name__ == "__main__":
	image = get_scanned_image()
	image = straighten_face(image)
	cropped_image = crop_image(image)
	cropped_image.save("cropped.jpg", "JPEG")
