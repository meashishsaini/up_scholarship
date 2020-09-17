# -*- coding: utf-8 -*-
import urllib.parse as urlparse
from datetime import datetime
import scrapy
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError
from scrapy.exceptions import CloseSpider
from up_scholarship.providers.constants import FormKeys, CommonData, TestStrings
from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers import utilities as utl
from up_scholarship.providers.url import UrlProviders
from up_scholarship.providers.codes import CodeFileReader
import logging

logger = logging.getLogger(__name__)

class BaseSpider(scrapy.Spider):

	def __init__(self, cls, *args, **kwargs):
		''' Load student's file and init variables'''
		super().__init__(cls, *args, **kwargs)
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
		self.bank = CodeFileReader(self.cd.bank_file)
		self.branch = CodeFileReader(self.cd.branch_file)
		self.course = CodeFileReader(self.cd.course_file)
		self.sub_caste = CodeFileReader(self.cd.sub_caste_file)
		self.tried = 0  # Number of times we have tried filling data for a students.
		self.i_students = 0  # Current student's index in student's list.
		self.err_students = []  # List of students we encountered error for.
		self.is_renewal = False  # Stores whether the current student is renewal.


	def process_errors(self, response, work_type, check_str, html=True):
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
				if error_in not in TestStrings.invalid_captcha:
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
			utl.save_file_with_name(student, response, work_type, str(datetime.today().year), is_debug=True)
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
	
	def errback_next(self, failure):
		""" Process network errors.
			Keyword arguments:
			failure -- previous scrapy network failure.
		"""
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

		# Close spider if we encounter above errors.
		student = self.students[self.i_students]
		student[FormKeys.status()] = error_str
		self.err_students.append(student)
		self.students[self.i_students] = student
		self.i_students = self.no_students
		self.save_if_done()
