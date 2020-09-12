import scrapy
from scrapy.exceptions import CloseSpider
from scrapy.spidermiddlewares.httperror import HttpError
import logging
from up_scholarship.providers import utilities as utl
from up_scholarship.providers.url import UrlProviders
from up_scholarship.providers.constants import CommonData, FormKeys, TestStrings, WorkType, FormSets, StdCategory
from up_scholarship.providers.codes import CodeFileReader
from up_scholarship.providers.student_file import StudentFile
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError
from datetime import datetime
import urllib.parse as urlparse
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string


class ReceiveAppSpider(scrapy.Spider):
	name = 'receive'
	tried = 0  # Number of times we have tried filling data for a students.
	no_students = 0  # Total number of students in the list.
	i_students = 0  # Current student's index in student's list.
	err_students = []  # List of students we encountered error for.
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.name(), FormKeys.institute(), FormKeys.final_submitted(),
		FormKeys.reg_year(), FormKeys.app_received(), FormKeys.religion()]
	school_type = "R"  # our school type

	def __init__(self, *args, **kwargs):
		""" Load student's file and init variables"""
		super(ReceiveAppSpider, self).__init__(*args, **kwargs)
		requests_logger = logging.getLogger('scrapy')
		requests_logger.setLevel(logging.ERROR)
		self.cd = CommonData()
		self.students = StudentFile().read_file(self.cd.students_in_file, self.cd.file_in_type)
		self.no_students = len(self.students)
		self.url_provider = UrlProviders(self.cd)
		self.is_renewal = False

		self.district = CodeFileReader(self.cd.district_file)
		self.institute = CodeFileReader(self.cd.institute_file)
		# self.caste = CodeFileReader(self.cd.caste_file)
		self.religion = CodeFileReader(self.cd.religion_file)

	# self.board = CodeFileReader(self.cd.board_file)

	def start_requests(self):
		""" Get institute login page"""
		self.i_students = self.skip_to_next_valid()
		self.save_if_done(raise_exc=False)
		if self.no_students > 0 and self.no_students != self.i_students:
			student = self.students[self.i_students]
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)

	def get_district(self, response):
		""" Fill the school district.
				Keyword arguments:
				response -- previous scrapy response.
		"""
		self.logger.info('In get school. Last URL: %s', response.url)
		if self.process_errors(response, TestStrings.error, captcha_check=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]
			# Extract hf for password
			hf = response.xpath('//*[@id="' + FormKeys.hf(FormSets.two) + '"]/@value').extract_first()
			form_data = {
				FormKeys.event_target(): FormKeys.district(form=True),
				FormKeys.district(form=True): self.district.get_code("rampur"),
				FormKeys.hf(FormSets.two, form=True): hf
			}
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.get_school_type,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def get_school_type(self, response):
		""" Fill the school district.
				Keyword arguments:
				response -- previous scrapy response.
		"""
		self.logger.info('In get school. Last URL: %s', response.url)
		if self.process_errors(response, TestStrings.error, captcha_check=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			# Extract hf for password
			hf = response.xpath('//*[@id="' + FormKeys.hf(FormSets.two) + '"]/@value').extract_first()
			form_data = {
				FormKeys.event_target(): FormKeys.school_type(form=True),
				FormKeys.district(form=True): self.district.get_code("rampur"),
				FormKeys.school_type(form=True): self.school_type,
				FormKeys.hf(FormSets.two, form=True): hf
			}
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.get_captcha,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def login_form(self, response):
		""" Login the form after getting captcha from previous response.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		self.logger.info('In login form. Last URL: %s', response.url)
		if self.process_errors(response, TestStrings.error, html=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]

			# Get captcha text from our ml model
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta['old_response']

			form_data = self.get_login_institute_data(
				student,
				captcha_value,
				self.school_type)
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.receive_page,
				errback=self.errback_next,
				dont_filter=True
			)
			yield request

	def receive_page(self, response):
		""" Open the receive application page
			Keyword arguments:
			response -- previous scrapy response.
		"""
		self.logger.info('In receive_page. Last URL: %s', response.url)
		student = self.students[self.i_students]
		if self.process_errors(response, TestStrings.error) or \
			response.url.lower().find(TestStrings.institute_login_success.lower()) == -1:
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			url = self.url_provider.get_institute_receive_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(
				url=url, callback=self.search_application_number, dont_filter=True, errback=self.errback_next)

	def search_application_number(self, response):
		""" Search the application number.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		self.logger.info('In search_application_number. Last URL: %s', response.url)
		if self.process_errors(response, TestStrings.error, captcha_check=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]
			app_type = '1' if self.is_renewal else '0'
			form_data = {
				FormKeys.application_type(form=True): app_type,
				FormKeys.registration_number_search(form=True): student.get(FormKeys.reg_no(), ''),
				FormKeys.search_button(form=True): FormKeys.search_button()
			}
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.receive_application,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def receive_application(self, response):
		""" Receive application if found.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		student = self.students[self.i_students]
		self.logger.info('In receive_application. Last URL: %s', response.url)
		app_id = response.xpath('//*[@id="%s"]//text()' % FormKeys.first_app_id())
		if self.process_errors(response, TestStrings.error, captcha_check=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		elif not app_id and app_id.extract_first() != student[FormKeys.reg_no()]:
			message = "Application registration number not found."
			self.logger.info(message)
			student[FormKeys.status()] = message
			self.students[self.i_students] = student
			self.i_students = self.i_students + 1
			self.i_students = self.skip_to_next_valid()
			self.save_if_done()
			url = self.url_provider.get_institute_receive_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(
				url=url, callback=self.search_application_number, dont_filter=True, errback=self.errback_next)
		else:
			form_data = {
				FormKeys.application_receive_agree(form=True): FormKeys.application_receive_agree(),
				FormKeys.application_receive_button(form=True): FormKeys.application_receive_button()
			}
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.parse,
				errback=self.errback_next,
				dont_filter=True
			)
			yield request

	def parse(self, response):
		""" Check if application is received.
					Keyword arguments:
					response -- previous scrapy response.
		"""
		self.logger.info('In parse. Last URL: %s', response.url)
		scripts = response.xpath('//script/text()').extract()
		application_received = scripts and scripts[0].find(TestStrings.application_received) != -1
		if not application_received and self.process_errors(response, TestStrings.error, captcha_check=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]
			if application_received:
				message = "Application successfully received.."
				student[FormKeys.status()] = message
				student[FormKeys.app_received()] = "Y"
			else:
				message = "Unable to receive application."
				student[FormKeys.status()] = message
				student[FormKeys.app_received()] = "N"
			self.logger.info(message)
			self.students[self.i_students] = student
			self.i_students = self.i_students + 1
			self.i_students = self.skip_to_next_valid()
			self.save_if_done()
			url = self.url_provider.get_institute_receive_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(
					url=url, callback=self.search_application_number, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		self.logger.info("In Captcha. Last URL " + response.url)
		if self.process_errors(response, TestStrings.error, html=True, captcha_check=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			# Use different callbacks for login form and fill data form.
			captcha_url = self.url_provider.get_captcha_url()
			callback = self.login_form
			request = scrapy.Request(url=captcha_url, callback=callback, dont_filter=True, errback=self.errback_next)
			request.meta['old_response'] = response
			yield request

	def save_if_done(self, raise_exc=True):
		""" Save student file if all students are done.
			Keyword arguments:
			raise_exc -- whether to raise close spider exception.
		"""
		if self.i_students >= self.no_students:
			st_file = StudentFile()
			utl.copy_file(self.cd.students_in_file, self.cd.students_old_file)
			st_file.write_file(
				self.students,
				self.cd.students_in_file,
				self.cd.students_out_file,
				self.cd.file_out_type)
			st_file.write_file(self.err_students, '', self.cd.students_err_file, self.cd.file_err_type)
			if raise_exc:
				raise CloseSpider('All students done')

	def skip_to_next_valid(self) -> int:
		"""	Check if data for required entries are available in the student's list and return index of it.
			Return valid student index or else no. of students.
			Returns: int
		"""
		length = len(self.students)
		return_index = -1
		for x in range(self.i_students, length):
			student = self.students[x]
			# If these required FormKeys are not available continue
			if not utl.check_if_keys_exist(student, self.common_required_keys):
				continue
			# We only support our own school for now
			if student.get(FormKeys.institute()).lower() != "parmeswari saran h s s shivpuri  block--suar":
				continue
			# Muslim student's have to be registered in different sites so skip them and also check non minority exists.
			if self.religion.get_code(student.get(FormKeys.religion(), '')) == self.religion.get_code("muslim"):
				continue
			reg_year = int(student.get(FormKeys.reg_year(), '')) if len(student.get(FormKeys.reg_year(), '')) > 0 else 0
			# Set return index if student is not marked for skipping,
			# registration year is current year and application is not filled.
			if student.get(FormKeys.skip(), '') == 'N' and reg_year == datetime.today().year and student.get(
					FormKeys.final_submitted(), '') == 'Y' and student.get(FormKeys.app_received(), '') == 'N':
				return_index = x
				# Also set the different sets of link used by up scholarship website.
				if utl.get_std_category(student[FormKeys.std()]) == StdCategory.pre:
					self.cd.set_form_set(FormSets.one)
				else:
					self.cd.set_form_set(FormSets.two)
				# If we have old registration no. in student's list set it to renewal.
				self.is_renewal = student.get(FormKeys.old_reg_no(), '') != ''
				if self.is_renewal:
					self.logger.info('Application is renewal')
				break
		# If return index is not -1 return it or else return total no. of students.
		if return_index != -1:
			student = self.students[return_index]
			self.logger.info(
				'Receiving application of: ' + student.get(FormKeys.name(), '') + ' of std: ' + student.get(
					FormKeys.std(), ''))
			return return_index
		else:
			return self.no_students

	def process_errors(self, response, check_str, html=True, captcha_check=True):
		""" Process error and skip to next student if max retries
			Arguments:
			response -- scrapy response
			check_str -- string if needed to check against
			html -- whether the response is html page
			captcha_check -- whether captcha error needed to be checked
			Returns: boolean
		"""
		student = self.students[self.i_students]
		parsed = urlparse.urlparse(response.url)
		parseq = urlparse.parse_qs(parsed.query)
		error = False
		errorstr = ''
		# If we match the check_str set it to generic error.
		if response.url.lower().find(check_str.lower()) != -1:
			error = True
			errorstr = 'Maximum retries reached'
		# Process code in url argument
		elif 'a' in parseq:
			error = True
			if parseq['a'][0] == 'c' and captcha_check:
				errorstr = 'captcha wrong'
			else:
				errorstr = 'Error code: ' + parseq['a'][0]
				self.tried = self.cd.max_tries
		# If the response is html, check for extra errors in the html page
		if html:
			error_in = response.xpath(
				'//*[@id="' + FormKeys.error_lbl(self.cd.current_form_set) + '"]/text()').extract_first()
			if error_in == TestStrings.invalid_captcha and captcha_check:
				error = True
				errorstr = 'captcha wrong'
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
			utl.save_file_with_name(student, response, WorkType.receive, str(datetime.today().year), is_debug=True)
			# Check if we have reached max retries and then move to other students, if available
			if self.tried >= self.cd.max_tries:
				student[FormKeys.status()] = errorstr
				self.logger.info(errorstr)
				self.students[self.i_students] = student
				self.err_students.append(student)
				self.i_students += 1
				self.tried = 0
				self.i_students = self.skip_to_next_valid()
				self.save_if_done()
			else:
				self.tried += 1
		return error

	def get_login_institute_data(self, student: dict, captcha_value: str, school_type: str) -> dict:
		""" Create and return the form data
					Keyword arguments:
					student -- student whose details needed to be filled.
					captcha_value -- captcha value to be used in filling form.
					Returns: dict
				"""
		std_c = utl.get_std_category(student.get(FormKeys.std(), ''))
		pre = std_c == StdCategory.pre
		password_hash, hd_text_hash = utl.get_login_institute_password("jlASG78g##cF")
		form_data = {
			FormKeys.district(form=True): self.district.get_code("rampur"),
			FormKeys.school_type(form=True): school_type,
			FormKeys.school_name(form=True): self.institute.get_code(student.get(FormKeys.institute())),
			FormKeys.text_password(form=True): password_hash,
			FormKeys.captcha_value(form=True): captcha_value,
			FormKeys.institute_login_button(form=True): FormKeys.institute_login_button(),
			FormKeys.hd_pass_text(form=True): hd_text_hash

		}
		return form_data

	def errback_next(self, failure):
		""" Process network errors.
			Keyword arguments:
			failure -- previous scrapy network failure.
		"""
		# log all failures
		self.logger.error(repr(failure))
		errorstr = repr(failure)
		if failure.check(HttpError):
			# these exceptions come from HttpError spider middleware
			response = failure.value.response
			self.logger.error('HttpError on %s', response.url)
			errorstr = 'HttpError on ' + response.url

		elif failure.check(DNSLookupError):
			# this is the original request
			request = failure.request
			self.logger.error('DNSLookupError on %s', request.url)
			errorstr = 'DNSLookupError on ' + request.url

		elif failure.check(TimeoutError, TCPTimedOutError):
			request = failure.request
			self.logger.error('TimeoutError on %s', request.url)
			errorstr = 'TimeoutError on ' + request.url

		# Close spider if we encounter above errors.
		student = self.students[self.i_students]
		student[FormKeys.status()] = errorstr
		self.err_students.append(student)
		self.students[self.i_students] = student
		self.i_students = self.no_students
		self.save_if_done()
