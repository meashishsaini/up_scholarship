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
	satisfy_criterias = []
	disatisfy_criterias = [] # Criteria which should be marked as N
	common_required_keys = []
	pre_required_keys = []
	post_required_keys = []

class BaseSpider(scrapy.Spider):

	def __init__(self, cls, skip_config: SkipConfig, auto_skip=True, *args, **kwargs):
		""" Load student"s file and init variables"""
		self.spider_name = self.name
		logging.getLogger("scrapy").setLevel(logging.ERROR)
		super().__init__(cls, *args, **kwargs)
		self.auto_skip = auto_skip
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
		if self.auto_skip:
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
				if self.auto_skip:
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
	
	def mark_is_renew(self):
		if self.student.get(FormKeys.old_reg_no()):
			logger.info("Application is renewal.")
			self.is_renewal = True
		else:
			logger.info("Application is not renewal.")
			self.is_renewal = False

	def skip_to_next_valid(self, raise_exc=True) -> int:
		self.student = None
		current_year = datetime.now().year
		self.tried = 0	# Set tried to 0 because we are most probably getting next student or none
		for self.current_student_index in range(self.current_student_index + 1, self.total_students):
			student = self.students[self.current_student_index]
			logger.info("Checking student: Name: %s Std: %s", student.get(FormKeys.name()), student.get(FormKeys.std()))
			if not utl.check_if_keys_exist(student, self.skip_config.common_required_keys):
				logger.warning("Common required keys not found. Keys: %s", self.skip_config.common_required_keys)
				continue
			std_category = utl.get_std_category(student[FormKeys.std()])
			if std_category is StdCategory.pre:
				if not utl.check_if_keys_exist(student, self.skip_config.pre_required_keys):
					logger.warning("Pre required keys not found. Keys: %s", self.skip_config.pre_required_keys)
					continue
			elif std_category is StdCategory.post:
				if not utl.check_if_keys_exist(student, self.skip_config.post_required_keys):
					logger.warning("Post required keys not found. Keys: %s", self.skip_config.post_required_keys)
					continue
			else:
				continue
			if student.get(FormKeys.skip()) == "Y":
				logger.warning("Marked for skipping.")
				continue
			skip_student = False
			for satisfy_criteria in self.skip_config.satisfy_criterias:
				if student.get(satisfy_criteria) != "Y":
					logger.warning("Criterias not satisfied. Criterias: %s", self.skip_config.satisfy_criterias)
					skip_student = True
					break
			for disatisfy_criteria in self.skip_config.disatisfy_criterias:
				if student.get(disatisfy_criteria) != "N":
					logger.warning("Disatisfy criterias not satisfied. Criterias: %s", self.skip_config.disatisfy_criterias)
					skip_student = True
					break
			if skip_student:
				continue
			student_reg_year = student.get(FormKeys.reg_year())
			if self.skip_config.check_valid_year:
				if not student_reg_year:
					logger.warning("No Registration year.")
					continue
				elif self.skip_config.allow_renew:
					if int(student_reg_year) != current_year-1:
						# We can't renew if there is more than one year gap between last scholarship
						logger.warning("Scholarship can't be renewed. Reg Year: %s", student_reg_year)
						continue
					if student.get(FormKeys.std()) != "11" and student.get(FormKeys.std()) != "09":
						# Renew can only be done for 9th and 11th
						logger.warning("Scholarship can't be renewed. Current std: %s", student.get(FormKeys.std()))
						continue
				elif int(student_reg_year) != current_year:
					logger.warning("Registration year is not current. Reg year: %s", student_reg_year)
					continue
			# Student already registered.
			elif student_reg_year:
				logger.warning("Student already registered. Current std: %s", student_reg_year)
				continue
			# We only support our own school for now and our school is till high school
			if student.get(FormKeys.institute()).lower() != "parmeswari saran h s s shivpuri  block--suar" and \
				utl.get_std_category(student.get(FormKeys.std())) == StdCategory.pre:
				logger.warning("Not our school. Institute: %s",  student.get(FormKeys.institute()))
				continue
			logger.info("Student selected: Name: %s Std: %s", student.get(FormKeys.name()), student.get(FormKeys.std()))
			self.student = student
			self.mark_is_renew()
			break
		if not self.student:
			self.save_and_done(raise_exc)
		
