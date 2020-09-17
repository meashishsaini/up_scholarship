# -*- coding: utf-8 -*-
import urllib.parse as urlparse
import scrapy
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError
from datetime import datetime
from up_scholarship.providers.constants import FormKeys, CommonData, TestStrings, WorkType
from up_scholarship.providers.file_name import FileName
from up_scholarship.providers import utilities as utl
from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers.url import UrlProviders
from scrapy.exceptions import CloseSpider
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
import logging

logger = logging.getLogger(__name__)

class RenewSpider(scrapy.Spider):
	name = 'renew'
	no_students = 0
	i_students = 0
	tried = 0
	err_students = []
	required_keys = [FormKeys.reg_year(), FormKeys.skip(), FormKeys.std(), FormKeys.name(), FormKeys.reg_no(),
																		FormKeys.dob(), FormKeys.mobile_no()]

	def __init__(self, *args, **kwargs):
		""" Load student's file and init variables"""
		super(RenewSpider, self).__init__(*args, **kwargs)
		logging.getLogger('scrapy').setLevel(logging.ERROR)
		self.cd = CommonData()
		self.students = StudentFile().read_file(self.cd.students_in_file, self.cd.file_in_type)
		self.no_students = len(self.students)
		self.url_provider = UrlProviders(self.cd)
		self.file_name_provider = FileName(WorkType.photo)

	def start_requests(self):
		self.i_students = self.skip_to_next_valid()
		self.save_if_done(raise_exc=False)
		if self.no_students > 0 and self.no_students != self.i_students:
			student = self.students[self.i_students]
			url = self.url_provider.get_renew_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def fill_form(self, response):
		logger.info('In fill form. Last URL: %s', response.url)
		if self.process_errors(response, TestStrings.error, html=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_renew_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True)
		else:
			student = self.students[self.i_students]
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta['old_response']
			form_data = {
				FormKeys.reg_no(form=True): student[FormKeys.reg_no()],
				FormKeys.dob(form=True): student[FormKeys.dob()],
				FormKeys.mobile_no(form=True): student.get(FormKeys.mobile_no(), ''),
				FormKeys.captcha_value(form=True): captcha_value,
				FormKeys.login(form=True): 'Submit',

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
		logger.info('In parse. Previous URL: %s', response.url)
		student = self.students[self.i_students]

		if response.url.find(TestStrings.renew_success) != -1:
			new_reg_no = response.xpath(
				'//*[@id="' + FormKeys.reg_no(form=True, reg=True) + '"]/text()').extract_first()
			vf_code = response.xpath('//*[@id="' + FormKeys.password(form=True, reg=True) + '"]/text()').extract_first()
			logger.info("----------------Application got renewed---------------")
			logger.info("New reg no.: %s vf_code: %s", new_reg_no, vf_code)
			print("----------------Application got renewed---------------")
			print("New reg no.:" + new_reg_no)
			src = utl.get_photo_by_uid_name(self.cd.data_dir, student, 'jpg ', student[FormKeys.reg_year()], FormKeys())
			student[FormKeys.old_reg_no()] = student[FormKeys.reg_no()]
			student[FormKeys.reg_no()] = new_reg_no
			student[FormKeys.password()] = vf_code
			student[FormKeys.status()] = "Success"
			student[FormKeys.std()] = str(int(student[FormKeys.std()]) + 1)
			#student[FormKeys.previous_school()] = student[FormKeys.institute()]
			student[FormKeys.reg_year()] = str(datetime.today().year)
			student = self.remove_old_values(student)
			dest = utl.get_photo_by_uid_name(
				self.cd.data_dir, student, 'jpg ', student[FormKeys.reg_year()], FormKeys())
			try:
				utl.copy_file(src, dest)
			except Exception as err:
				print(err)
			self.students[self.i_students] = student
			utl.save_file_with_name(student, response, WorkType.renew, str(datetime.today().year))
			self.i_students += 1
			self.i_students = self.skip_to_next_valid()
			self.tried = 0
		else:
			if not self.process_errors(response, TestStrings.renew_form):
				if not self.process_errors(response, TestStrings.error):
					self.process_errors(response, TestStrings.registration_new)
		self.save_if_done()
		student = self.students[self.i_students]
		url = self.url_provider.get_renew_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def errback_next(self, failure):
		""" Process network errors.
			Keyword arguments:
			failure -- previous scrapy network failure.
		"""
		# log all failures
		logger.error(repr(failure))
		errorstr = repr(failure)
		if failure.check(HttpError):
			# these exceptions come from HttpError spider middleware
			response = failure.value.response
			logger.error('HttpError on %s', response.url)
			errorstr = 'HttpError on ' + response.url

		elif failure.check(DNSLookupError):
			# this is the original request
			request = failure.request
			logger.error('DNSLookupError on %s', request.url)
			errorstr = 'DNSLookupError on ' + request.url

		elif failure.check(TimeoutError, TCPTimedOutError):
			request = failure.request
			logger.error('TimeoutError on %s', request.url)
			errorstr = 'TimeoutError on ' + request.url

		# Close spider if we encounter above errors.
		student = self.students[self.i_students]
		student[FormKeys.status()] = errorstr
		self.err_students.append(student)
		self.students[self.i_students] = student
		self.i_students = self.no_students
		self.save_if_done()

	def get_captcha(self, response):
		logger.info("In Captcha. Last URL %s", response.url)
		if self.process_errors(response, TestStrings.error):
			student = self.students[self.i_students]
			url = self.url_provider.get_renew_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_url = self.url_provider.get_captcha_url()

			request = scrapy.Request(url=captcha_url, callback=self.fill_form, dont_filter=True, errback=self.errback_next)
			request.meta['old_response'] = response
			yield request

	def skip_to_next_valid(self) -> int:
		length = len(self.students)
		for x in range(self.i_students, length):
			student = self.students[x]
			# If these required keys are not available continue
			if not utl.check_if_keys_exist(student, self.required_keys):
				logger.info('skipping ' + student[FormKeys.name()])
				continue
			reg_year = int(student.get(FormKeys.reg_year(), '0')) if len(student.get(FormKeys.reg_year(), '')) > 0 else 0
			if reg_year != 0 and reg_year < datetime.today().year and student[FormKeys.skip()] == 'N':
				if student[FormKeys.std()] == '9' or student[FormKeys.std()] == '11':
					print('Renewing application of: ' + student[FormKeys.name()] + ' reg_no: ' + student[
						FormKeys.reg_no()] + ' of std: ' + student[FormKeys.std()])
					return x
				elif student[FormKeys.std()] == '10':
					print('Upgrading student: %s %s of std: %s reg_year: %s' % (
						student[FormKeys.name()], student[FormKeys.reg_no()], student[FormKeys.std()], student[FormKeys.reg_year()]))
					src = utl.get_photo_by_uid_name(
						self.cd.data_dir, student, 'jpg ', student[FormKeys.reg_year()], FormKeys())
					student[FormKeys.std()] = '11'
					student[FormKeys.reg_year()] = ''
					student[FormKeys.status()] = ''
					student[FormKeys.reg_no()] = ''
					student[FormKeys.old_reg_no()] = ''
					student[FormKeys.previous_school()] = ''
					student[FormKeys.password()] = ''
					student = self.remove_old_values(student)
					dest = utl.get_photo_by_uid_name(
						self.cd.data_dir, student, 'jpg ', str(datetime.today().year), FormKeys())
					utl.copy_file(src, dest)
					self.students[x] = student
				elif student[FormKeys.std()] == '12':
					student[FormKeys.skip()] = 'Y'
					self.students[x] = student
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
		""" Save student file if all students are done.
			Keyword arguments:
			raise_exc -- whether to raise close spider exception.
		"""
		if self.i_students >= self.no_students:
			st_file = StudentFile()
			utl.copy_file(self.cd.students_in_file, self.cd.students_old_file)
			st_file.write_file(self.students, self.cd.students_in_file, self.cd.students_out_file, self.cd.file_out_type)
			st_file.write_file(self.err_students, '', self.cd.students_err_file, self.cd.file_err_type)
			if raise_exc:
				raise CloseSpider('All students done')

	def remove_old_values(self, student: dict) -> dict:
		# student[FormKeys.lastyear_std()] = ''
		# student[FormKeys.last_year_result()] = ''
		# student[FormKeys.lastyear_total_marks()] = ''
		# student[FormKeys.lastyear_obtain_marks()] = ''
		# student[FormKeys.admission_date()] = ''
		# student[FormKeys.tuition_fees()] = ''
		# student[FormKeys.lastyear_scholarship_amt()] = ''
		# student[FormKeys.fees_receipt_no()] = ''
		# student[FormKeys.total_fees_left()] = ''
		# student[FormKeys.total_fees_submitted()] = ''
		# student[FormKeys.total_fees()] = ''
		# student[FormKeys.fees_receipt_date()] = ''
		# student[FormKeys.board_reg_no()] = ''
		# student[FormKeys.institute()] = ''
		student[FormKeys.app_filled()] = 'N'
		student[FormKeys.photo_uploaded()] = 'N'
		student[FormKeys.submitted_for_check()] = 'N'
		student[FormKeys.final_submitted()] = 'N'
		student[FormKeys.final_printed()] = 'N'
		student[FormKeys.app_received()] = 'N'
		student[FormKeys.app_verified()] = 'N'
		student[FormKeys.app_forwarded()] = 'N'
		return student
