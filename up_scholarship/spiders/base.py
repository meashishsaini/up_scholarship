import urllib.parse as urlparse
from datetime import datetime
import scrapy
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError
from scrapy.exceptions import CloseSpider
import logging
from dataclasses import dataclass
from datetime import datetime

from up_scholarship.providers.constants import FormKeys, CommonData, TestStrings, StdCategory
from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers import utilities as utl
from up_scholarship.providers.url import UrlProviders
from up_scholarship.providers.codes import CodeFileReader

logger = logging.getLogger(__name__)

@dataclass
class SkipConfig:
	check_valid_year = True
	allow_renew = False
	satisfy_criteria = ""
	common_required_keys = []
	pre_required_keys = []
	post_required_keys = []

class BaseSpider(scrapy.Spider):

	def __init__(self, cls, skip_config: SkipConfig, *args, **kwargs):
		""" Load student"s file and init variables"""
		self.spider_name = self.name
		logging.getLogger("scrapy").setLevel(logging.ERROR)
		super().__init__(cls, *args, **kwargs)
		self.cd = CommonData()
		self.students = StudentFile().read_file(self.cd.students_in_file, self.cd.file_in_type)
		self.total_students = len(self.students)
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
		self.current_student_index = 0  # Current student"s index in student"s list.
		self.err_students = []  # List of students we encountered error for.
		self.is_renewal = False  # Stores whether the current student is renewal.
		self.skip_config = skip_config
		self.student = None
		self.skip_to_next_valid(raise_exc=False)



	def process_errors(self, response, check_strings: list, html=True):
		""" Process error and skip to next student if max retries
			Arguments:
			response -- scrapy response
			check_string -- strings list if needed to check against
			html -- whether the response is html page
			Returns: boolean
		"""
		parsed = urlparse.urlparse(response.url)
		parseq = urlparse.parse_qs(parsed.query)
		error = False
		errorstr = ""
		# They are ordered for preference of error
		# If we match the check_str set it to generic error.
		for check_string in check_strings:
			if response.url.lower().find(check_string.lower()) != -1:
				error = True
				errorstr = "Unknown error occured"
		# Process code in url argument
		if "a" in parseq:
			error = True
			if parseq["a"][0] == "c":
				errorstr = "captcha wrong"
			else:
				errorstr = "Error code: " + parseq["a"][0]
				self.tried = self.cd.max_tries
		# If the response is html, check for extra errors in the html page
		if html:
			error_in = response.xpath(
				"//*[@id='" + FormKeys.error_lbl() + "']/text()").extract_first()
			if error_in:
				errorstr = error_in
				error = True
				if error_in not in TestStrings.invalid_captcha:
					self.tried = self.cd.max_tries
				if error_in == TestStrings.aadhaar_auth_failed:
					self.student[FormKeys.skip()] = "Y"
			# Check if error messages are in scripts
			else:
				scripts = response.xpath("//script/text()").extract()
				for script in scripts:
					if 10 < len(script) < 120 and script.find(TestStrings.alert) != -1:
						errorstr = script[7:-1]
						self.tried = self.cd.max_tries
						error = True
					# If we have error save page as html file.
		if error:
			logger.info("Error string: %s", errorstr)
			utl.save_file_with_name(self.student, response, self.spider_name, str(datetime.today().year), tried=self.tried, is_debug=True)
			# Check if we have reached max retries and then move to other students, if available
			if self.tried >= self.cd.max_tries:
				self.student[FormKeys.status()] = errorstr
				self.students[self.current_student_index] = self.student
				self.err_students.append(self.student)
				self.skip_to_next_valid()
			else:
				self.tried += 1
		return error

	def save_and_done(self, raise_exc=True):
		st_file = StudentFile()
		utl.copy_file(self.cd.students_in_file, self.cd.students_old_file)
		st_file.write_file(self.students, self.cd.students_in_file, self.cd.students_out_file, self.cd.file_out_type)
		st_file.write_file(self.err_students, "", self.cd.students_err_file, self.cd.file_err_type)
		if raise_exc:
			raise CloseSpider("All students done")
	
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
			logger.error("HttpError on %s", response.url)
			error_str = "HttpError on " + response.url

		elif failure.check(DNSLookupError):
			# this is the original request
			request = failure.request
			logger.error("DNSLookupError on %s", request.url)
			error_str = "DNSLookupError on " + request.url

		elif failure.check(TimeoutError, TCPTimedOutError):
			request = failure.request
			logger.error("TimeoutError on %s", request.url)
			error_str = "TimeoutError on " + request.url

		# Close spider if we encounter above errors.
		self.student[FormKeys.status()] = error_str
		self.err_students.append(self.student)
		self.students[self.current_student_index] = self.student
		self.save_and_done()

	def skip_to_next_valid(self, raise_exc=True) -> int:
		self.student = None
		current_year = datetime.now().year
		self.tried = 0	# Set tried to 0 because we are most probably getting next student or none
		for self.current_student_index in range(self.current_student_index + 1, self.total_students):
			student = self.students[self.current_student_index]
			if not utl.check_if_keys_exist(student, self.skip_config.common_required_keys):
				continue
			std_category = utl.get_std_category(student[FormKeys.std()])
			if std_category is StdCategory.pre:
				if not utl.check_if_keys_exist(student, self.skip_config.pre_required_keys):
					continue
			elif std_category is StdCategory.post:
				if not utl.check_if_keys_exist(student, self.skip_config.post_required_keys):
					continue
			else:
				continue
			if student.get(FormKeys.skip()) is "Y":
				continue
			if self.skip_config.satisfy_criteria and student.get(self.self.skip_config.satisfy_criteria) is not "Y":
				continue
			student_reg_year = student.get(FormKeys.reg_year())
			if self.skip_config.check_valid_year:
				if not student_reg_year:
					continue
				elif self.skip_config.allow_renew:
					if int(student_reg_year) is not current_year-1:
						# We can't renew if there is more than one year gap between last scholarship
						continue
				elif int(student_reg_year) is not current_year:
					continue
			elif student_reg_year:
				continue
			self.student = student
			break
		if not self.student:
			self.save_and_done(raise_exc)
		
