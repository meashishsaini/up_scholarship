import urllib.parse as urlparse
import scrapy
from datetime import datetime
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings, StdCategory, FormSets
from up_scholarship.spiders.base import BaseSpider
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class AadhaarAuthSpider(BaseSpider):
	name = 'aadhaarauth'
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.reg_no(), FormKeys.dob(), FormKeys.name(), FormKeys.app_filled(),
		FormKeys.photo_uploaded(), FormKeys.father_name(), FormKeys.submitted_for_check(), FormKeys.aadhaar_authenticated()
	]

	def __init__(self, *args, **kwargs):
		""" Load student's file and init variables"""
		super().__init__(AadhaarAuthSpider, *args, **kwargs)

	def start_requests(self):
		self.i_students = self.skip_to_next_valid()
		self.save_if_done(raise_exc=False)
		if self.no_students > 0 and self.no_students != self.i_students:
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def login_form(self, response):
		logger.info('In login form. Last Url: %s', response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
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
		""" If we get popup about accepting terms accept them and if not continue filling other things.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In accept popup. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error, TestStrings.login]):
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
			url = self.url_provider.get_aadhaar_auth_url(student.get(FormKeys.std(), ''), app_id, self.is_renewal)
			logger.info("URL: %s", url)
			request = scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
			request.meta['old_response'] = response
			yield request
		# Popup might not have been accepted, accept it
		else:
			logger.info('Accepting popup. Last URL: %s', response.url)
			request = scrapy.FormRequest.from_response(
				response,
				formdata={
					FormKeys.check_popup_agree(form=True)	: 'on',
					FormKeys.popup_button(form=True)		: 'Proceed >>>',
				},
				callback=self.accept_popup,
				errback=self.errback_next,
				dont_filter=True,
			)
			yield request

	def fill_data(self, response):
		""" Fill the aadhaar number.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In fill data. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_value = get_captcha_string(response.body)

			student = self.students[self.i_students]
			# Get old response after getting captcha
			response = response.meta['old_response']
			form_data = self.get_fill_form_data(student, captcha_value)
			logger.info(form_data)
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.parse,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def parse(self, response):
		logger.info('In parse. Last URL: %s', response.url)
		student = self.students[self.i_students]
		correct_label = response.xpath(
			'//*[@id="' + FormKeys.correct_lbl() + '"]/text()').extract_first()
		logger.info("Correct label: %s", correct_label)
		correct_label = correct_label if correct_label else ""
		if response.url.lower().find(TestStrings.app_default) == -1 and correct_label == TestStrings.aadhaar_authenticated:
			student[FormKeys.aadhaar_authenticated()] = 'Y'
			student[FormKeys.status()] = 'Success'
			self.students[self.i_students] = student
			logger.info("----------------Aadhaar got authenticated---------------")
			print("----------------Aadhaar got authenticated---------------")
			self.i_students += 1
			self.i_students = self.skip_to_next_valid()
			self.tried = 0
		else:
			self.process_errors(response, [TestStrings.app_default, TestStrings.aadhaar_auth, TestStrings.error])
		self.save_if_done()
		student = self.students[self.i_students]
		url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		logger.info("In Captcha. Last URL: " + response.url)
		if self.process_errors(response, [TestStrings.error]):
			self.save_if_done()
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			# Use different callbacks for login form and fill data form.
			captcha_url = self.url_provider.get_captcha_url()
			if response.url.lower().find(TestStrings.login) != -1:
				callback = self.login_form
			else:
				callback = self.fill_data
			request = scrapy.Request(url=captcha_url, callback=callback, dont_filter=True,
									 errback=self.errback_next)
			request.meta['old_response'] = response
			yield request

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
					FormKeys.app_filled(), '') == 'Y' and student.get(FormKeys.photo_uploaded(), '') == 'Y' and student.get(
					FormKeys.aadhaar_authenticated(), '') == 'N':
				return_index = x
				if utl.get_std_category(student[FormKeys.std()]) == StdCategory.pre:
					self.cd.set_form_set(FormSets.one)
				else:
					self.cd.set_form_set(FormSets.four)
				if student.get(FormKeys.old_reg_no(), '') != '':
					self.is_renewal = True
					logger.info('Application is renewal')
					if utl.get_std_category(student[FormKeys.std()]) == StdCategory.pre:
						self.cd.set_form_set(FormSets.four)
				else:
					self.is_renewal = False
				break
		if (return_index != -1):
			student = self.students[return_index]
			logger.info('Aadhaar authenticating application of: ' + student.get(FormKeys.name(), '') + ' of std: ' + student.get(
				FormKeys.std(), ''))
			return return_index
		else:
			return self.no_students

	def get_fill_form_data(self, student: dict, captcha_value: str) -> dict:
		""" Create and return the form data
			Keyword arguments:
			student -- student whose details needed to be filled.
			captcha_value -- captcha value to be used in filling form.
			Returns: dict
		"""
		enrypted_aadhaar_no = utl.get_encryped_aadhaar(student.get(FormKeys.aadhaar_no(),''))
		form_data = {
			FormKeys.aadhaar_no(form = True)		:	enrypted_aadhaar_no,
			FormKeys.aadhaar_no_re(form = True)		:	enrypted_aadhaar_no,
			FormKeys.captcha_value(form=True)		:	captcha_value,
			FormKeys.check_agree(form=True)			:	'on',
			FormKeys.submit(form=True)				:	'Verify Aadhar'
		}
		return form_data
