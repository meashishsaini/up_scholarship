# -*- coding: utf-8 -*-
import urllib.parse as urlparse
from datetime import datetime
import scrapy
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError
from scrapy.exceptions import CloseSpider
from up_scholarship.providers.constants import FormKeys, CommonData, TestStrings, WorkType, StdCategory, FormSets
from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers import utilities as utl
from up_scholarship.providers.url import UrlProviders
from up_scholarship.providers.codes import CodeFileReader
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
import logging

logger = logging.getLogger(__name__)

class RegisterSpider(scrapy.Spider):
	name = 'register'
	tried = 0  # Number of times we have tried filling data for a students.
	no_students = 0  # Total number of students in the list.
	i_students = 0  # Current student's index in student's list.
	err_students = []  # List of students we encountered error for.
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.name(), FormKeys.dob(), FormKeys.district(), FormKeys.institute(),
		FormKeys.caste(), FormKeys.father_name(), FormKeys.mother_name(), FormKeys.gender(), FormKeys.board()]
	pre_required_keys = [FormKeys.eight_passing_year(), FormKeys.eight_school()]
	post_required_keys = [FormKeys.high_school_passing_year(), FormKeys.high_school_roll_no(), FormKeys.high_school_name_address()]

	def __init__(self, *args, **kwargs):
		''' Load student's file and init variables'''
		super(RegisterSpider, self).__init__(*args, **kwargs)
		logging.getLogger('scrapy').setLevel(logging.ERROR)
		self.cd = CommonData()
		self.students = StudentFile().read_file(self.cd.students_in_file, self.cd.file_in_type)
		self.no_students = len(self.students)
		self.url_provider = UrlProviders(self.cd)
		self.district = CodeFileReader(self.cd.district_file)
		self.institute = CodeFileReader(self.cd.institute_file)
		self.caste = CodeFileReader(self.cd.caste_file)
		self.religion = CodeFileReader(self.cd.religion_file)
		self.board = CodeFileReader(self.cd.board_file)

	def start_requests(self):
		""" Get registration page if we have some students"""
		self.i_students = self.skip_to_next_valid()
		self.save_if_done(raise_exc=False)
		if self.no_students > 0 and self.no_students != self.i_students:
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)

	def get_district(self, response):
		logger.info('In getting district. Last Url: %s', response.url)
		if self.process_errors(response, TestStrings.error):
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True)
		else:
			student = self.students[self.i_students]
			form_data = {
				FormKeys.event_target()     : FormKeys.district(form=True),
				FormKeys.district(form=True): self.district.get_code(student[FormKeys.district()])
			}
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.get_institute,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def get_institute(self, response):
		logger.info('In getting institute. Last Url: %s', response.url)
		if self.process_errors(response, TestStrings.error):
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True)
		else:
			student = self.students[self.i_students]
			form_data = {
				FormKeys.event_target()			: FormKeys.institute(form=True),
				FormKeys.district(form=True)	: self.district.get_code(student[FormKeys.district()]),
				FormKeys.institute(form=True)	: self.institute.get_code(student[FormKeys.institute()])
			}
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.get_caste,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def get_caste(self, response):
		logger.info('In get caste. Last Url: %s', response.url)
		if self.process_errors(response, TestStrings.error):
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True)
		else:
			student = self.students[self.i_students]
			form_data = {
				FormKeys.event_target()      : FormKeys.caste(form=True),
				FormKeys.district(form=True) : self.district.get_code(student[FormKeys.district()]),
				FormKeys.institute(form=True): self.institute.get_code(student[FormKeys.institute()]),
			}
			if student[FormKeys.is_minority()] == 'Y':
				form_data[FormKeys.caste(form=True)] = self.caste.get_code('min')
			else:
				form_data[FormKeys.caste(form=True)] = self.caste.get_code(student[FormKeys.caste()])
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.get_captcha,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def fill_reg(self, response):
		logger.info('In reg form. Last Url: %s', response.url)
		if self.process_errors(response, TestStrings.error, html=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_institute, dont_filter=True)
		else:
			student = self.students[self.i_students]
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta['old_response']

			form_data, password = self.get_form_data(student, captcha_value)
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.parse,
				errback=self.errback_next,
				dont_filter=True
			)
			request.meta['password'] = password
			yield request

	def parse(self, response):
		logger.info('In parse. Last URL: %s ', response.url)
		student = self.students[self.i_students]

		if response.url.find(TestStrings.registration_success) != -1:
			reg_no = response.xpath('//*[@id="' + FormKeys.reg_no(form=True, reg=True) + '"]/text()').extract_first()
			student[FormKeys.reg_no()] = reg_no
			student[FormKeys.password()] = response.meta['password']
			student[FormKeys.status()] = "Success"
			student[FormKeys.reg_year()] = str(datetime.today().year)
			self.students[self.i_students] = student
			logger.info("----------------Application got registered---------------")
			logger.info("Reg no.: %s password: %s", reg_no, response.meta['password'])
			utl.save_file_with_name(student, response, WorkType.register, str(datetime.today().year))
			self.i_students += 1
			self.i_students = self.skip_to_next_valid()
			self.tried = 0
		else:
			if not self.process_errors(response, TestStrings.registration_form):
				self.process_errors(response, TestStrings.error)
		self.save_if_done()
		student = self.students[self.i_students]
		url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
		yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)

	def errback_next(self, failure):
		# log all failures
		logger.error(repr(failure))
		error_str = repr(failure)

		if failure.check(HttpError):
			# these exceptions come from HttpError spider middleware
			response = failure.value.response
			logger.error('HttpError on %s', response.url)
			error_str = 'HttpError on ' + response.url

		elif failure.check(DNSLookupError):
			# this is the original request
			request = failure.request
			logger.error('DNSLookupError on %s', request.url)
			error_str = 'DNSLookupError on ' + request.url

		elif failure.check(TimeoutError, TCPTimedOutError):
			request = failure.request
			logger.error('TimeoutError on %s', request.url)
			error_str = 'TimeoutError on ' + request.url

		student = self.students[self.i_students]
		student[FormKeys.status()] = error_str
		self.err_students.append(student)
		self.students[self.i_students] = student
		self.i_students = self.no_students
		self.save_if_done()

	def get_captcha(self, response):
		print("In Captcha. Last URL: " + response.url)
		if self.process_errors(response, TestStrings.error):
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_url = self.url_provider.get_captcha_url()
			request = scrapy.Request(url=captcha_url, callback=self.fill_reg, dont_filter=True,
									 errback=self.errback_next)
			request.meta['old_response'] = response
			yield request

	def skip_to_next_valid(self) -> int:
		length = len(self.students)
		return_index = -1
		for x in range(self.i_students, length):
			student = self.students[x]
			# If these required FormKeys are not available continue
			if not utl.check_if_keys_exist(student, self.common_required_keys):
				continue
			std_cat = utl.get_std_category(student[FormKeys.std()])
			if std_cat == StdCategory.pre and not utl.check_if_keys_exist(student, self.pre_required_keys):
				continue
			elif std_cat == StdCategory.post and not utl.check_if_keys_exist(student, self.post_required_keys):
				continue
			elif std_cat == StdCategory.unknown:
				continue
			reg_year = int(student.get(FormKeys.reg_year(), '')) if len(student.get(FormKeys.reg_year(), '')) > 0 else 0

			if student[FormKeys.skip()] == 'N' and reg_year == 0:
				return_index = x
				student[FormKeys.reg_no()] = ''
				student[FormKeys.old_reg_no()] = ''
				self.students[x] = student
				break

		if return_index != -1:
			student = self.students[return_index]
			print('Registering application of: ' + student[FormKeys.name()] + ' of std: ' + student[FormKeys.std()])
			return return_index
		else:
			return self.no_students

	def process_errors(self, response, check_str, html=True):
		''' Process error and skip to next student if max retries
			Arguments:
			response -- scrapy response
			check_str -- string if needed to check against
			html -- whether the response is html page
			Returns: boolean
		'''
		student = self.students[self.i_students]
		parsed = urlparse.urlparse(response.url)
		parseq = urlparse.parse_qs(parsed.query)
		error = False
		errorstr = ''
		# If we match the check_str set it to generic error.
		if response.url.lower().find(check_str.lower()) != -1:
			error = True
			errorstr = 'Unknown error occured'
		# Process code in url argument
		elif 'a' in parseq:
			error = True
			if parseq['a'][0] == 'c':
				errorstr = 'captcha wrong'
			else:
				errorstr = 'Error code: ' + parseq['a'][0]
				self.tried = self.cd.max_tries
		# If the response is html, check for extra errors in the html page
		if html:
			error_in = response.xpath(
				'//*[@id="' + FormKeys.error_lbl() + '"]/text()').extract_first()
			if error_in:
				errorstr = error_in
				error = True
				if error_in != TestStrings.invalid_captcha and error_in != TestStrings.invalid_captcha_2:
					self.tried = self.cd.max_tries
				if error_in == TestStrings.aadhaar_auth_failed:
					student[FormKeys.skip()] = "Y"
			# Check if error messages are in scripts
			else:
				scripts = response.xpath('//script/text()').extract()
				for script in scripts:
					if 10 < len(script) < 120 and script.find(TestStrings.alert) != -1:
						errorstr = script[7:-1]
						self.tried = self.cd.max_tries
						error = True
					# If we have error save page as html file.
		if error:
			logger.info("Error string: %s", errorstr)
			utl.save_file_with_name(student, response, WorkType.aadhaar_auth, str(datetime.today().year), is_debug=True)
			# Check if we have reached max retries and then move to other students, if available
			if self.tried >= self.cd.max_tries:
				student[FormKeys.status()] = errorstr
				self.students[self.i_students] = student
				self.err_students.append(student)
				self.i_students += 1
				self.tried = 0
				self.i_students = self.skip_to_next_valid()
				self.save_if_done()
			else:
				self.tried += 1
		return error

	def save_if_done(self, raise_exc=True):
		if self.i_students >= self.no_students:
			st_file = StudentFile()
			utl.copy_file(self.cd.students_in_file, self.cd.students_old_file)
			st_file.write_file(self.students, self.cd.students_in_file, self.cd.students_out_file, self.cd.file_out_type)
			st_file.write_file(self.err_students, '', self.cd.students_err_file, self.cd.file_err_type)
			if raise_exc:
				raise CloseSpider('All students done')

	def get_form_data(self, student: dict, captcha_value):
		father_husband_name = ''
		if student[FormKeys.father_name()] != '':
			father_husband_name = student[FormKeys.father_name()]
		else:
			father_husband_name = student[FormKeys.husband_name()]
		password = utl.get_random_password()
		hashed_password, _ = utl.get_login_form_password(password)
		form_data = {
			FormKeys.district(form=True)           : self.district.get_code(student[FormKeys.district()]),
			FormKeys.institute(form=True)          : self.institute.get_code(student[FormKeys.institute()]),
			FormKeys.religion(form=True)           : self.religion.get_code(student[FormKeys.religion()]),
			FormKeys.name(form=True)               : student[FormKeys.name()],
			FormKeys.father_name(form=True)        : father_husband_name,
			FormKeys.mother_name(form=True)        : student[FormKeys.mother_name()],
			FormKeys.dob(form=True, reg=True)      : student[FormKeys.dob()],
			FormKeys.gender(form=True)             : student[FormKeys.gender()],
			FormKeys.board(form=True)              : self.board.get_code(student[FormKeys.board()]),
			FormKeys.mobile_no(form=True, reg=True): student[FormKeys.mobile_no()],
			FormKeys.password(form=True)           : hashed_password,
			FormKeys.confirm_password(form=True)   : hashed_password,
			FormKeys.captcha_value(form=True)      : captcha_value,
			FormKeys.submit(form=True)             : 'Submit',
		}
		if student[FormKeys.is_minority()] == 'Y':
			form_data[FormKeys.caste(form=True)] = self.caste.get_code('min')
		else:
			form_data[FormKeys.caste(form=True)] = self.caste.get_code(student[FormKeys.caste()])
		if utl.get_std_category(student[FormKeys().std()]) == StdCategory.pre:
			form_data[FormKeys.eight_passing_year(form=True)] = student[FormKeys.eight_passing_year()]
			form_data[FormKeys.eight_school(form=True)] = student[FormKeys.eight_school()]

		else:
			form_data[FormKeys.high_school_passing_year(form=True)] = student[FormKeys.high_school_passing_year()]
			form_data[FormKeys.high_school_roll_no(form=True)] = student[FormKeys.high_school_roll_no()]
			form_data[FormKeys.high_school_name_address(form=True)] = student[FormKeys.high_school_name_address()]
		return form_data, password
