# -*- coding: utf-8 -*-
import os
import urllib.request
import urllib.parse as urlparse
import scrapy
import hashlib
from up_scholarship.providers.constants import FormKeys, CommonData, TestStrings, StdCategory, FormSets, WorkType
from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers.url import UrlProviders
from up_scholarship.providers import utilities as utl
from datetime import datetime
from scrapy.exceptions import CloseSpider
import mimetypes
import io
import codecs
from pathlib import Path
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers.codes import CodeFileReader
from scrapy.http import Request
import logging

logger = logging.getLogger(__name__)

class UploadPhotoSpider(scrapy.Spider):
	name = 'uploadphoto'
	tried = 0
	no_students = 0
	i_students = 0
	err_students = []
	is_renewal = False
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.reg_no(), FormKeys.dob(), FormKeys.name(), FormKeys.app_filled(),
		FormKeys.photo_uploaded(), FormKeys.father_name()]
	non_minority_keys = [
		FormKeys.subcaste(), FormKeys.caste_cert_issue_date(), FormKeys.caste_cert_name(), FormKeys.caste_cer_app_no(),
		FormKeys.caste_cert_no()]
	post_required_keys = [
		FormKeys.high_school_obtain_marks(), FormKeys.high_school_total_marks(), FormKeys.total_fees(),
		FormKeys.tuition_fees(), FormKeys.total_fees_submitted(), FormKeys.fees_receipt_no(),
		FormKeys.fees_receipt_date(), FormKeys.total_fees_left()]

	def __init__(self, *args, **kwargs):
		''' Load student's file and init variables'''
		super(UploadPhotoSpider, self).__init__(*args, **kwargs)
		self.cd = CommonData()
		self.students = StudentFile().read_file(self.cd.students_in_file, self.cd.file_in_type)
		self.no_students = len(self.students)
		self.url_provider = UrlProviders(self.cd)
		self.religion = CodeFileReader(self.cd.religion_file)
		logging.getLogger('scrapy').setLevel(logging.ERROR)

	def start_requests(self):
		self.i_students = self.skip_to_next_valid()
		self.save_if_done(raise_exc=False)
		if self.no_students > 0 and self.no_students != self.i_students:
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def login_form(self, response):
		logger.info('In login form. Last Url: %s', response.url)
		if self.process_errors(response, TestStrings.error, html=False):
			self.save_if_done()
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta['old_response']

			# Extract hf for password
			hf = response.xpath('//*[@id="' + FormKeys.hf(self.cd.current_form_set) + '"]/@value').extract_first()

			form_data = utl.get_login_form_data(student, hf, self.is_renewal, captcha_value, FormKeys(), self.cd.current_form_set)
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.accept_popup,
				errback=self.errback_next,
				dont_filter=True
			)
			yield request

	def accept_popup(self, response):
		''' If we get popup about accepting terms accept them and if not continue filling other things.
			Keyword arguments:
			response -- previous scrapy response.
		'''
		logger.info('In accept popup. Last URL: %s', response.url)
		if self.process_errors(response, TestStrings.error) or self.process_errors(response, TestStrings.login):
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		# Got default response, means popup has been accepted.
		elif response.url.lower().find(TestStrings.app_default) != -1:
			logger.info('Got default response url %s', response.url)
			# Extract appid for url
			parsed = urlparse.urlparse(response.url)
			app_id = urlparse.parse_qs(parsed.query)['Appid'][0]

			student = self.students[self.i_students]
			url = self.url_provider.get_photo_up_url(student.get(FormKeys.std(), ''), app_id, self.is_renewal)
			logger.info("URL: %s", url)
			yield scrapy.Request(url=url, callback=self.upload_photo, dont_filter=True, errback=self.errback_next)
		# Popup might not have been accepted, accept it
		else:
			logger.info('Accepting popup. Last URL: %s', response.url)
			request = scrapy.FormRequest.from_response(
				response,
				formdata={
					FormKeys.check_popup_agree(form=True): 'on',
					FormKeys.popup_button(form=True): 'Proceed >>>',
				},
				callback=self.accept_popup,
				errback=self.errback_next,
				dont_filter=True,
			)
			yield request

	def upload_photo(self, response):
		logger.info('In upload photo. Last URL: %s', response.url)
		if self.process_errors(response, TestStrings.error, html=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			headers = response.request.headers

			parsed = urlparse.urlparse(response.url)
			app_id = urlparse.parse_qs(parsed.query)['Appid'][0]
			student = self.students[self.i_students]
			url = self.url_provider.get_photo_up_url(student.get(FormKeys.std(), ''), app_id, self.is_renewal)

			viewstate = response.xpath('//*[@id="' + FormKeys.view_state() + '"]/@value').extract_first()
			viewstategenerater = response.xpath \
				('//*[@id="' + FormKeys.view_state_generator() + '"]/@value').extract_first()
			eventvalidation = response.xpath('//*[@id="' + FormKeys.event_validation() + '"]/@value').extract_first()

			filename = utl.get_photo_by_uid_name(self.cd.data_dir, student, 'jpg ', student[FormKeys.reg_year()], FormKeys())
			if utl.check_if_file_exists(filename):
				pre = utl.get_std_category(student[FormKeys.std()]) == StdCategory.pre

				fields = [(FormKeys.view_state(), viewstate),
						(FormKeys.view_state_generator(), viewstategenerater),
						(FormKeys.view_state_encrypted(), ''),
						(FormKeys.event_validation(), eventvalidation),
						(FormKeys.upload_photo(self.cd.current_form_set, form=True),
							'Upload Photo')]
				if not pre:
					fields.append((FormKeys.is_pic_upload(), "Y"))
					fields.append((FormKeys.is_handi_upload(), ""))
					fields.append((FormKeys.handi_type(), "0"))

				files = [(FormKeys.upload_photo_name(form=True), student[FormKeys.aadhaar_no()] + ".jpg", open(filename, 'rb'))]
				logger.info('Photo file %s', files)
				logger.info('Photo fields %s', fields)
				content_type, body = utl.MultipartFormDataEncoder().encode(fields, files)
				headers['Content-Type'] = content_type
				headers['Content-length'] = str(len(body))

				request_with_cookies = Request(url=url, method='POST', headers=headers, body=body, dont_filter=True)
				yield request_with_cookies
			else:
				student[FormKeys.status()] = 'Photo file not found'
				self.students[self.i_students] = student
				self.i_students += 1
				self.i_students = self.skip_to_next_valid()
				self.save_if_done()
				student = self.students[self.i_students]
				url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
				yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def parse(self, response):
		logger.info('Parse Got URL: %s', response.url)
		student = self.students[self.i_students]

		upload_status = ''
		scripts = response.xpath('//script/text()').extract()
		for script in scripts:
			if len(script) > 10 and script.lower().find(TestStrings.alert) != -1:
				upload_status = script[7:-1]
				break
		if upload_status.lower().find(TestStrings.photo_uploaded) != -1:
			student[FormKeys.photo_uploaded()] = 'Y'
			student[FormKeys.status()] = 'Success'
			self.students[self.i_students] = student
			logger.info("----------------Photo successfully uploaded---------------")
			print("----------------Photo successfully uploaded---------------")
			self.i_students += 1
			self.i_students = self.skip_to_next_valid()
			self.tried = 0
		else:
			if not self.process_errors(response, TestStrings.photo_upload):
				self.process_errors(response, TestStrings.error)
		self.save_if_done()
		student = self.students[self.i_students]
		url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def errback_next(self, failure):
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
		student = self.students[self.i_students]
		student[FormKeys.status()] = errorstr
		self.err_students.append(student)
		self.students[self.i_students] = student
		self.i_students = self.no_students
		self.save_if_done()

	def get_captcha(self, response):
		print("In Captcha: " + response.url)
		if self.process_errors(response, TestStrings.error):
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_url = self.url_provider.get_captcha_url()
			if response.url.lower().find(TestStrings.login) != -1:
				request = scrapy.Request(url=captcha_url, callback=self.login_form, dont_filter=True,
										 errback=self.errback_next)
			else:
				request = scrapy.Request(url=captcha_url, callback=self.upload_photo, dont_filter=True,
										 errback=self.errback_next)
			request.meta['old_response'] = response
			yield request

	def save_if_done(self, raise_exc=True):
		''' Save student file if all students are done.
			Keyword arguments:
			raise_exc -- whether to raise close spider exception.
		'''
		if self.i_students >= self.no_students:
			st_file = StudentFile()
			utl.copy_file(self.cd.students_in_file, self.cd.students_old_file)
			st_file.write_file(self.students, self.cd.students_in_file, self.cd.students_out_file, self.cd.file_out_type)
			st_file.write_file(self.err_students, '', self.cd.students_err_file, self.cd.file_err_type)
			if raise_exc:
				raise CloseSpider('All students done')

	def skip_to_next_valid(self) -> int:
		'''	Check if data for required entries are available in the student's list and return index of it.
			Return valid student index or else no. of students.
			Returns: int
		'''
		length = len(self.students)
		return_index = -1
		for x in range(self.i_students, length):
			student = self.students[x]
			# If these required FormKeys are not available continue
			if not utl.check_if_keys_exist(student, self.common_required_keys):
				continue
			std_c = utl.get_std_category(student.get(FormKeys.std(), ''))
			if std_c == StdCategory.post and not utl.check_if_keys_exist(student, self.post_required_keys):
				continue
			elif std_c == StdCategory.unknown:
				continue
			# Muslim student's have to be registered in different sites so skip them and also check non minority exists.
			elif self.religion.get_code(student.get(FormKeys.religion(), '')) == self.religion.get_code("muslim") \
					and not utl.check_if_keys_exist(student, self.non_minority_keys):
				continue
			reg_year = int(student.get(FormKeys.reg_year(), '')) if len(student.get(FormKeys.reg_year(), '')) > 0 else 0
			# Set return index if student is not marked for skipping, registration year is current year and
			# application is not filled.
			if student[FormKeys.skip()] == 'N' and reg_year == datetime.today().year and student[
				FormKeys.app_filled()] == 'Y' and student[FormKeys.photo_uploaded()] == 'N':
				return_index = x
				# Also set the different sets of link used by up scholarship website.
				if utl.get_std_category(student[FormKeys.std()]) == StdCategory.pre:
					self.cd.set_form_set(FormSets.one)
				else:
					self.cd.set_form_set(FormSets.four)
				# If we have old registration no. in student's list set it to renewal.
				if student.get(FormKeys.old_reg_no(), '') != '':
					self.is_renewal = True
					logger.info('Application is renewal')
					if utl.get_std_category(student[FormKeys.std()]) == StdCategory.pre:
						self.cd.set_form_set(FormSets.four)
				else:
					self.is_renewal = False
				break
		# If return index is not -1 return it or else return total no. of students.
		if (return_index != -1):
			student = self.students[return_index]
			logger.info('Uploading photo of: ' + student[FormKeys.name()] + ' of std: ' + student[FormKeys.std()])
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
