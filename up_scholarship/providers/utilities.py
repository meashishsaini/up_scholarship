import string
import os
import hashlib
import codecs
import mimetypes
import sys
import uuid
import shutil
from up_scholarship.providers.constants import WorkType, StdCategory
from up_scholarship.providers.file_name import FileName
from up_scholarship.providers.constants import FormKeys
from pathlib import Path
import imutils
import cv2
import io
from Crypto.Cipher import AES
import base64
import binascii
try:
	from StringIO import StringIO
except ImportError:
	from io import StringIO

class PKCS7Encoder(object):
	def __init__(self, k=16):
		self.k = k

	def decode(self, text):
		'''
		Remove the PKCS#7 padding from a text string
		'''
		nl = len(text)
		val = int(binascii.hexlify(text[-1]), 16)
		if val > self.k:
			raise ValueError('Input is not padded or padding is corrupt')

		l = nl - val
		return text[:l]

	def encode(self, text):
		'''
		Pad an input string according to PKCS#7
		'''
		l = len(text)
		output = StringIO()
		val = self.k - (l % self.k)
		for _ in range(val):
			output.write('%02x' % val)
		return text.encode("utf-8") + binascii.unhexlify(output.getvalue())
def save_file_with_name(
		student,
		response,
		work_type: WorkType,
		year: str,
		extension="html",
		extra=None,
		is_debug=False):
	filename = FileName(work_type).get(student, extension, year, extra=extra, is_debug=is_debug)
	os.makedirs(os.path.dirname(filename), exist_ok=True)
	with open(filename, 'wb') as f:
		f.write(response.body)


def get_photo_by_uid_name(data_dir: str, student, extension: str, reg_year: str, keys: FormKeys, is_file=True):
	return_str = data_dir + 'photos/by_UID/' + reg_year + '/' + student[keys.std()]
	if is_file:
		return_str = return_str + '/' + student[keys.aadhaar_no()] + "." + extension
	return return_str


def get_random_password(length=8):
	"""	Make custom passwords for the website in the format aaaANc

		Keyword arguments:
		length -- length of the password; default to 6
	"""
	lower = string.ascii_lowercase
	upper = string.ascii_uppercase
	digits = string.digits
	s_character = "@#$&"
	password = ''
	for _ in range(int(length / 2)):
		password += lower[ord(os.urandom(1)) % len(lower)]
	for _ in range((int(length / 2)) - 2):
		password += upper[ord(os.urandom(1)) % len(upper)]
	password += digits[ord(os.urandom(1)) % len(digits)]
	password += s_character[ord(os.urandom(1)) % len(s_character)]
	return password

def get_encryped_aadhaar(aadhaar_no: str):
	encoder = PKCS7Encoder()
	key = '8080808080808080'.encode("utf-8")
	cipher = AES.new( key, AES.MODE_CBC, key )
	pad_text = encoder.encode(aadhaar_no)
	cipered = cipher.encrypt(pad_text)
	return (base64.b64encode(cipered)).decode("utf-8")

def get_login_form_password(password: str, hf: str = ''):
	"""	Password is hashed and concatenated with hashed hf found in page

		Keyword arguments:
		password -- use this password to generate hash
		hf -- string to append at teh start of the password
	"""
	rnd_hash = ''
	if hf:
		rnd = hf.encode('utf-8')
		rnd_hash = hashlib.sha512(rnd).hexdigest()
	pwd_hash = rnd_hash + hashlib.sha512(password.encode('utf-8')).hexdigest()
	return pwd_hash, rnd_hash


def get_login_institute_password(password: str):
	"""	Password is hashed using sha512 and hd text using md5

		Keyword arguments:
		password -- use this password to generate hash
		return pwd hash and ht text hash
	"""
	pwd_hash = hashlib.sha512(password.encode('utf-8')).hexdigest()
	hd_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
	return pwd_hash, hd_hash


def check_if_keys_exist(data: dict, in_keys: list) -> bool:
	keys = data.keys()
	for in_key in in_keys:
		for key in keys:
			if in_key == key:
				return True
	return False


def get_std_category(std: str) -> StdCategory:
	if std == '9' or std == '10':
		return StdCategory.pre
	elif std == '11' or std == '12':
		return StdCategory.post
	else:
		return StdCategory.unknown


class MultipartFormDataEncoder(object):
	def __init__(self):
		self.boundary = uuid.uuid4().hex
		self.content_type = 'multipart/form-data; boundary={}'.format(self.boundary)

	@classmethod
	def u(cls, s):
		if sys.hexversion < 0x03000000 and isinstance(s, str):
			s = s.decode('utf-8')
		if sys.hexversion >= 0x03000000 and isinstance(s, bytes):
			s = s.decode('utf-8')
		return s

	def iter(self, fields, files):
		"""
			Keyword arguments:
			fields -- fields is a sequence of (name, value) elements for regular form fields.
			files -- files is a sequence of (name, filename, file-type) elements for data to be uploaded as files
			Yield body's chunk as bytes
		"""
		encoder = codecs.getencoder('utf-8')
		for (key, value) in fields:
			key = self.u(key)
			yield encoder('--{}\r\n'.format(self.boundary))
			yield encoder(self.u('Content-Disposition: form-data; name="{}"\r\n').format(key))
			yield encoder('\r\n')
			if isinstance(value, int) or isinstance(value, float):
				value = str(value)
			yield encoder(self.u(value))
			yield encoder('\r\n')
		for (key, filename, fd) in files:
			key = self.u(key)
			filename = self.u(filename)
			yield encoder('--{}\r\n'.format(self.boundary))
			yield encoder(self.u('Content-Disposition: form-data; name="{}"; filename="{}"\r\n').format(key, filename))
			yield encoder(
				'Content-Type: {}\r\n'.format(mimetypes.guess_type(filename)[0] or 'application/octet-stream'))
			yield encoder('\r\n')
			with fd:
				buff = fd.read()
				yield (buff, len(buff))
			yield encoder('\r\n')
		yield encoder('--{}--\r\n'.format(self.boundary))

	def encode(self, fields, files):
		body = io.BytesIO()
		for chunk, _ in self.iter(fields, files):
			body.write(chunk)
		return self.content_type, body.getvalue()


def move_file(source: str, destination: str) -> bool:
	try:
		os.makedirs(os.path.dirname(destination), exist_ok=True)
		shutil.move(source, destination)
		return True
	except shutil.Error as err:
		print('file move error: ' + err.args[0])
		return False
	except OSError as why:
		print('file move error: ' + str(why))


# def copy_file(source: str, destination: str) -> bool:
# 	try:
# 		os.makedirs(os.path.dirname(destination), exist_ok=True)
# 		shutil.copy(source, destination)
# 		return True
# 	except shutil.Error as err:
# 		print('file copy error: ' + err.args[0])
# 		return False
# 	except OSError as why:
# 		print('file copy error: ' + str(why))


def copy_file(source: str, destination: str) -> bool:
	try:
		os.makedirs(os.path.dirname(destination), exist_ok=True)
		shutil.copy(source, destination)
		return True
	except shutil.Error as err:
		print('file copy error: ' + err.args[0])
		return False
	except OSError as why:
		print('file copy error: ' + str(why))


def get_save_file(student: dict, tried=-1) -> str:
	if tried == -1:
		name = student['std'] + '/' + student['name'] + '.' + student['father_name'] + '.' + student['mother_name']
	else:
		name = student['std'] + '/' + student['name'] + '.' + student['father_name'] + '.' + student[
			'mother_name'] + str(tried)
	return name


def get_login_form_data(student: dict, hf: str, is_renewal: bool, captcha_value: str, keys: FormKeys, form_set):
	password = student.get(keys.password(), '')
	hashed_password, hashed_hf = get_login_form_password(password, hf)
	form_data = {
		keys.login_reg_no(form=True)	: student.get(keys.reg_no(), ''),
		keys.dob(form=True)				: student.get(keys.dob(), ''),
		keys.password(form=True)		: hashed_password,
		keys.captcha_value(form=True)	: captcha_value,
		keys.login(form=True)			: 'Submit',
		keys.hf(form_set, form=True)	: hashed_hf,
		keys.renewal_button(form=True)	: '2' if is_renewal else '1'}
	if get_std_category(student.get(keys.std(), '')) == StdCategory.pre:
		form_data[keys.login_type(form=True)] = '1'
	else:
		form_data[keys.login_type(form=True)] = '2'
	return form_data


def check_if_file_exists(filename):
	pfile = Path(filename)
	return pfile.is_file()


def resize_to_fit(image, width, height):
	"""A helper function to resize an image to fit within a given size.
		Keyword arguments:
		image -- image to resize
		width -- desired width in pixels
		height -- desired height in pixels
		Returns: the resized image
	"""

	# grab the dimensions of the image, then initialize
	# the padding values
	(h, w) = image.shape[:2]

	# if the width is greater than the height then resize along
	# the width
	if w > h:
		image = imutils.resize(image, width=width)

	# otherwise, the height is greater than the width so resize
	# along the height
	else:
		image = imutils.resize(image, height=height)

	# determine the padding values for the width and height to
	# obtain the target dimensions
	padW = int((width - image.shape[1]) / 2.0)
	padH = int((height - image.shape[0]) / 2.0)

	# pad the image then apply one more resizing to handle any
	# rounding issues
	image = cv2.copyMakeBorder(image, padH, padH, padW, padW, cv2.BORDER_CONSTANT, value=[255, 255, 255])
	image = cv2.resize(image, (width, height))

	# return the pre-processed image
	return image
