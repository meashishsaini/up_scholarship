# -*- coding: utf-8 -*-
import os
import urllib.request
import urllib.parse as urlparse
import scrapy
import hashlib
from datetime import datetime
from scrapy.exceptions import CloseSpider
from up_scholarship.providers.constants import FormKeys, CommonData, TestStrings, StdCategory, FormSets, WorkType
from up_scholarship.providers import utilities as utl
from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers.url import UrlProviders
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
import logging
from up_scholarship.providers.codes import CodeFileReader


class FinalSubmitDataSpider(scrapy.Spider):
	name = 'finalsubmit'
	tried = 0
	no_students = 0
	i_students = 0
	err_students = []
	is_renewal = False
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.reg_no(), FormKeys.dob(), FormKeys.name(), FormKeys.app_filled(),
		FormKeys.photo_uploaded(), FormKeys.father_name(), FormKeys.submitted_for_check(), FormKeys.final_submitted()
	]

	def __init__(self, *args, **kwargs):
		''' Load student's file and init variables'''
		super(FinalSubmitDataSpider, self).__init__(*args, **kwargs)
		requests_logger = logging.getLogger('scrapy')
		requests_logger.setLevel(logging.ERROR)
		self.cd = CommonData()
		self.students = StudentFile().read_file(self.cd.students_in_file, self.cd.file_in_type)
		self.no_students = len(self.students)
		self.url_provider = UrlProviders(self.cd)
		self.religion = CodeFileReader(self.cd.religion_file)

	def start_requests(self):
		self.i_students = self.skip_to_next_valid()
		self.save_if_done(raise_exc=False)
		if self.no_students > 0 and self.no_students != self.i_students:
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def login_form(self, response):
		self.logger.info('In login form. Last URL: %s', response.url)
		if self.process_errors(response, TestStrings.error, html=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta['old_response']

			# Extract hf for password
			hf = response.xpath('//*[@id="' + FormKeys.hf(self.cd.current_form_set) + '"]/@value').extract_first()

			form_data = utl.get_login_form_data(student, hf, self.is_renewal, captcha_value, FormKeys(),
												self.cd.current_form_set)
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.accept_popup,
				errback=self.errback_next,
				dont_filter=True
			)
			yield request

	def accept_popup(self, response):
		self.logger.info('In accept popup. Last URL: %s', response.url)
		if self.process_errors(response, TestStrings.error) or self.process_errors(response, TestStrings.login):
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		elif response.url.lower().find(TestStrings.app_default) != -1:
			# Extract appid for url
			self.logger.info('Got default response url %s', response.url)
			student = self.students[self.i_students]
			everything_fine, status = self.check_if_matched(response,
															self.religion.get_code(student[FormKeys.religion()]),
															utl.get_std_category(
																student[FormKeys.std()]) == StdCategory.pre)
			if everything_fine:
				parsed = urlparse.urlparse(response.url)
				app_id = urlparse.parse_qs(parsed.query)['Appid'][0]
				std = student.get(FormKeys.std(), '')
				if std == '12':
					url = self.url_provider.get_final_print_url(student.get(FormKeys.std(), ''), app_id,
																self.is_renewal)
					request = scrapy.Request(url=url, callback=self.save_print, dont_filter=True,
											 errback=self.errback_next)
				else:
					url = self.url_provider.get_final_disclaimer_url(student.get(FormKeys.std(), ''), app_id,
																	 self.is_renewal)
					request = scrapy.Request(url=url, callback=self.final_disclaimer, dont_filter=True,
											 errback=self.errback_next)
			# request.meta['old_response'] = response
			else:
				student[FormKeys.status()] = status
				self.err_students.append(student)
				self.students[self.i_students] = student
				self.tried
				self.i_students += 1
				self.i_students = self.skip_to_next_valid()
				self.save_if_done()
				student = self.students[self.i_students]
				url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
				request = scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True,
										 errback=self.errback_next)
			yield request
		else:
			self.logger.info('Accepting popup. Last URL: %s', response.url)
			request = scrapy.FormRequest.from_response(
				response,
				formdata={
					FormKeys.check_popup_agree(form=True): 'on',
					FormKeys.popup_button(form=True)     : 'Proceed >>>',
				},
				callback=self.accept_popup,
				errback=self.errback_next,
				dont_filter=True,
			)
			yield request

	def final_disclaimer(self, response):
		self.logger.info('In Final disclaimer. Last URL: %s', response.url)
		student = self.students[self.i_students]
		if response.url.lower().find(TestStrings.final_disclaimer.lower()) != -1:
			parsed = urlparse.urlparse(response.url)
			app_id = urlparse.parse_qs(parsed.query)['Appid'][0]

			url = self.url_provider.get_final_print_url(student.get(FormKeys.std(), ''), app_id, self.is_renewal)
			request = scrapy.Request(url=url, callback=self.save_print, dont_filter=True, errback=self.errback_next)

		elif response.url.lower().find(TestStrings.final_print) != -1:
			self.logger.info('Saving student\'s final page')
			utl.save_file_with_name(student, response, WorkType.final_submit, str(datetime.today().year),
									extra="/finalprint")

			img_url = response.xpath('//*[@id="PhotoImg"]/@src').extract_first()
			parsed = urlparse.urlparse(img_url)
			app_id = urlparse.parse_qs(parsed.query)['App_Id'][0]

			url = self.url_provider.get_img_print_url(student.get(FormKeys.std(), ''), app_id, self.is_renewal)
			request = scrapy.Request(url=url, callback=self.save_img, dont_filter=True, errback=self.errback_next)
		else:
			self.process_errors(response, TestStrings.app_default)
			self.process_errors(response, TestStrings.error)
			self.save_if_done()
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			request = scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		yield request

	def save_print(self, response):
		self.logger.info('In save print. Last URL: %s', response.url)
		if response.url.lower().find(TestStrings.final_print) != -1:
			student = self.students[self.i_students]

			self.logger.info('Saving student\'s final page')
			utl.save_file_with_name(student, response, WorkType.final_submit, str(datetime.today().year),
									extra="/finalprint")

			img_url = response.xpath('//*[@id="PhotoImg"]/@src').extract_first()
			parsed = urlparse.urlparse(img_url)
			app_id = urlparse.parse_qs(parsed.query)['App_Id'][0]

			url = self.url_provider.get_img_print_url(student.get(FormKeys.std(), ''), app_id, self.is_renewal)
			request = scrapy.Request(url=url, callback=self.save_img, dont_filter=True, errback=self.errback_next)
			# request.meta['old_response'] = response.meta['old_response']
			yield request
		else:
			self.process_errors(response, TestStrings.app_default)
			self.process_errors(response, TestStrings.error)
			self.save_if_done()
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def save_img(self, response):
		self.logger.info('In save img. Last URL: %s', response.url)
		if response.url.lower().find(TestStrings.show_image) != -1:
			student = self.students[self.i_students]
			parsed = urlparse.urlparse(response.url)
			f = parsed.path.split('/')
			f = f[len(f) - 1]

			self.logger.info('Saving student\'s image')
			utl.save_file_with_name(student, response, WorkType.final_submit, str(datetime.today().year), extension="",
									extra='/' + f)

			student[FormKeys.final_submitted()] = 'Y'
			student[FormKeys.status()] = 'Success'
			self.students[self.i_students] = student
			self.logger.info("----------------Application got saved for instituion---------------")
			print("----------------Application got saved for instituion---------------")
			self.i_students += 1
			self.i_students = self.skip_to_next_valid()
			self.tried = 0
		else:
			self.process_errors(response, TestStrings.app_default)
			self.process_errors(response, TestStrings.error)
		self.save_if_done()
		student = self.students[self.i_students]
		url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def errback_next(self, failure):
		''' Process network errors.
			Keyword arguments:
			failure -- previous scrapy network failure.
		'''
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

	def get_captcha(self, response):
		print("In Captcha. Last URL: " + response.url)
		if self.process_errors(response, TestStrings.error, html=True, captcha_check=False):
			self.save_if_done()
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_url = self.url_provider.get_captcha_url()
			request = scrapy.Request(url=captcha_url, callback=self.login_form, dont_filter=True,
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
		length = len(self.students)
		return_index = -1
		for x in range(self.i_students, length):
			student = self.students[x]
			# If these required keys are not available continue
			if not utl.check_if_keys_exist(student, self.common_required_keys):
				continue
			reg_year = int(student.get(FormKeys.reg_year(), '')) if len(student.get(FormKeys.reg_year(), '')) > 0 else 0
			if student.get(FormKeys.skip(), '') == 'N' and reg_year == datetime.today().year and student.get(
					FormKeys.app_filled(), '') == 'Y' and student.get(FormKeys.photo_uploaded(),  '') == 'Y' and student.get(
					FormKeys.submitted_for_check(), '') == 'Y' and student.get(FormKeys.final_submitted(), '') == 'N':
				return_index = x
				if utl.get_std_category(student[FormKeys.std()]) == StdCategory.pre:
					self.cd.set_form_set(FormSets.one)
				else:
					self.cd.set_form_set(FormSets.four)
				if student.get(FormKeys.old_reg_no(), '') != '':
					self.is_renewal = True
					print('is renewal')
					if utl.get_std_category(student[FormKeys.std()]) == StdCategory.pre:
						self.cd.set_form_set(FormSets.four)
				else:
					self.is_renewal = False
				break
		if return_index != -1:
			student = self.students[return_index]
			print(
				'Saving application of: ' + student.get(FormKeys.name(), '') + ' of std: ' + student.get(FormKeys.std(), ''))
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
			utl.save_file_with_name(student, response, WorkType.final_submit, str(datetime.today().year), is_debug=True)
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

	def check_if_matched(self, response, religion, pre):
		income_cert_no_status = self.get_status(response, FormKeys.income_cert_no_status(self.cd.current_form_set))
		caste_cert_no_status = self.get_status(response, FormKeys.caste_cert_no_status(self.cd.current_form_set))
		annual_income_status = self.get_status(response, FormKeys.annual_income_status(self.cd.current_form_set))
		final_form_status = self.get_status(response, FormKeys.final_form_status(self.cd.current_form_set))
		high_school_status = self.get_status(response, FormKeys.high_school_status(self.cd.current_form_set))
		old = self.cd.current_form_set
		self.cd.set_form_set(FormSets.two)

		if income_cert_no_status is None:
			income_cert_no_status = self.get_status(response, FormKeys.income_cert_no_status(self.cd.current_form_set))
		if caste_cert_no_status is None:
			caste_cert_no_status = self.get_status(response, FormKeys.caste_cert_no_status(self.cd.current_form_set))
		if annual_income_status is None:
			annual_income_status = self.get_status(response, FormKeys.annual_income_status(self.cd.current_form_set))
		if final_form_status is None:
			final_form_status = self.get_status(response, FormKeys.final_form_status(self.cd.current_form_set))
		if high_school_status is None:
			high_school_status = self.get_status(response, FormKeys.high_school_status(self.cd.current_form_set))

		self.cd.set_form_set(old)
		self.logger.info(
			str(final_form_status) + ' ' + str(income_cert_no_status) + ' ' + str(caste_cert_no_status) + ' ' + str(
				annual_income_status))
		ok = True
		status = ''
		if final_form_status is None or len(final_form_status) < 4:
			if income_cert_no_status is None or str(income_cert_no_status).lower() != TestStrings.matched:
				status += "Income cert no status: " + str(income_cert_no_status) + '; '
				ok = False
			if religion != self.religion.get_code('muslim') and (
					caste_cert_no_status is None or str(caste_cert_no_status).lower() != TestStrings.matched):
				status += "Caste cert no status: " + str(caste_cert_no_status) + '; '
				ok = False
			if annual_income_status is None or str(annual_income_status).lower() != TestStrings.matched:
				status += "Annual income status: " + str(annual_income_status) + '; '
				ok = False
			if not pre and (high_school_status is None or str(high_school_status).lower() != TestStrings.matched):
				status += "High school status: " + str(high_school_status) + '; '
				ok = False
		else:
			ok = False
			status = final_form_status
		if ok:
			status = 'Success'
		print(status)
		return ok, status

	def get_status(self, response, key: str):
		return response.xpath('//*[@id="' + key + '"]').xpath('normalize-space()').extract_first()
