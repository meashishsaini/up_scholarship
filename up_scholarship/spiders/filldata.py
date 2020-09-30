import urllib.parse as urlparse
import scrapy
from datetime import datetime
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings, StdCategory, FormSets
from up_scholarship.spiders.base import BaseSpider, SkipConfig
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class FillDataSpider(BaseSpider):
	"""	UP scholarship form fill spider.
	"""
	name = 'filldata'
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.reg_no(), FormKeys.dob(), FormKeys.district(),
		FormKeys.lastyear_total_marks(), FormKeys.lastyear_obtain_marks(), FormKeys.annual_income(),
		FormKeys.income_cert_app_no(), FormKeys.income_cert_no(), FormKeys.income_cert_issue_date(),
		FormKeys.income_cert_name(), FormKeys.bank_account_no(), FormKeys.bank_name(),
		FormKeys.branch_name(), FormKeys.bank_account_holder_name(), FormKeys.admission_date(), FormKeys.board(),
		FormKeys.previous_school(), FormKeys.permanent_address_1(), FormKeys.permanent_address_2()]
	pre_required_keys = []
	non_minority_keys = [
		FormKeys.subcaste(), FormKeys.caste_cert_issue_date(), FormKeys.caste_cert_name(), FormKeys.caste_cer_app_no(),
		FormKeys.caste_cert_no()]
	post_required_keys = [
		FormKeys.high_school_obtain_marks(), FormKeys.high_school_total_marks(), FormKeys.total_fees(),
		FormKeys.tuition_fees(), FormKeys.total_fees_submitted(), FormKeys.fees_receipt_no(),
		FormKeys.fees_receipt_date(),
		FormKeys.total_fees_left()]

	def __init__(self, *args, **kwargs):
		""" Load student's file and init variables"""
		skip_config = SkipConfig()
		skip_config.common_required_keys = self.common_required_keys
		skip_config.pre_required_keys = self.pre_required_keys
		skip_config.post_required_keys = self.post_required_keys
		skip_config.disatisfy_criterias = [FormKeys.app_filled()]
		super().__init__(FillDataSpider, skip_config, *args, **kwargs)

	def start_requests(self):
		""" Load student's file and get login page if we have some students"""
		if self.student:
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def login_form(self, response):
		""" Login the form after getting captcha from previous response.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In login form. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			# Get captcha text from our ml model
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta['old_response']

			# Extract hf for password
			hf = response.xpath('//*[@id="' + FormKeys.hf(self.cd.current_form_set) + '"]/@value').extract_first()

			form_data = utl.get_login_form_data(
				self.student,
				hf,
				self.is_renewal,
				captcha_value,
				FormKeys(),
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
		""" If we get popup about accepting terms accept them and if not continue filling other things.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In accept popup. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error, TestStrings.login]):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		# Got default response, means popup has been accepted.
		elif response.url.lower().find(TestStrings.app_default) != -1:
			logger.info('Got default response url %s', response.url)
			# Extract appid for url
			parsed = urlparse.urlparse(response.url)
			app_id = urlparse.parse_qs(parsed.query)['Appid'][0]

			url = self.url_provider.get_fill_reg_url(self.student.get(FormKeys.std(), ''), app_id, self.is_renewal)
			logger.info("URL: %s", url)
			yield scrapy.Request(url=url, callback=self.get_bankname, dont_filter=True, errback=self.errback_next)
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

	def get_bankname(self, response):
		""" Fill the bank name.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In get bankname. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			form_data = {
				FormKeys.event_target()			: FormKeys.bank_name(form=True),
				FormKeys.bank_name(form=True)	: self.bank.get_code(self.student.get(FormKeys.bank_name(), ''))
			}
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.get_bankdist,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def get_bankdist(self, response):
		""" Fill the bank district.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In get bankdist. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			form_data = {
				FormKeys.event_target()							: FormKeys.branch_dist_name(form=True),
				FormKeys.bank_name(form=True)					: self.bank.get_code(self.student.get(FormKeys.bank_name(), '')),
				FormKeys.branch_dist_name(form=True)			: self.district.get_code("rampur")
			}
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.get_branchname,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def get_branchname(self, response):
		""" Fill the bank branch name.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In get branchname. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			form_data = {
				FormKeys.event_target()					: FormKeys.branch_name(form=True),
				FormKeys.bank_name(form=True)			: self.bank.get_code(
																self.student.get(FormKeys.bank_name(), '')),
				FormKeys.branch_dist_name(form=True)	: self.district.get_code("rampur"),
				FormKeys.branch_name(form=True)			: self.branch.get_code(
																self.student.get(FormKeys.bank_name(), ''),
																self.student.get(FormKeys.branch_name(), ''))
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

	def fill_data(self, response):
		""" Fill the other form data which does not required page to be refreshed.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In fill data. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_value = get_captcha_string(response.body)
			# Get old response after getting captcha
			response = response.meta['old_response']
			form_data = self.get_fill_form_data(self.student, captcha_value)
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
		""" Parse the form to check if the form is really filled.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In Parse. Last URL: %s', response.url)
		if response.url.lower().find(TestStrings.app_new_filled.lower()) != -1 or response.url.lower().find(
				TestStrings.app_renew_filled.lower()) != -1:
			self.student[FormKeys.app_filled()] = 'Y'
			self.student[FormKeys.status()] = 'Success'
			self.students[self.current_student_index] = self.student
			logger.info("----------------Application got filled---------------")
			self.skip_to_next_valid()
		else:
			self.process_errors(response, [TestStrings.app_fill_form, TestStrings.error])
		url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ''), self.is_renewal)
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		logger.info("In Captcha. Last URL " + response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			# Use different callbacks for login form and fill data form.
			captcha_url = self.url_provider.get_captcha_url()
			if response.url.lower().find(TestStrings.login) != -1:
				callback = self.login_form
			else:
				callback = self.fill_data
			request = scrapy.Request(url=captcha_url, callback=callback, dont_filter=True, errback=self.errback_next)
			request.meta['old_response'] = response
			yield request

	def get_fill_form_data(self, student: dict, captcha_value: str) -> dict:
		""" Create and return the form data
			Keyword arguments:
			student -- student whose details needed to be filled.
			captcha_value -- captcha value to be used in filling form.
			Returns: dict
		"""
		std_c = utl.get_std_category(self.student.get(FormKeys.std(), ''))
		pre = std_c == StdCategory.pre
		form_data = {
			FormKeys.last_year_result(form=True)					: self.student.get(FormKeys.last_year_result(), 'P'),
			FormKeys.lastyear_total_marks(form=True)				: self.student.get(FormKeys.lastyear_total_marks(), ''),
			FormKeys.lastyear_obtain_marks(form=True)				: self.student.get(FormKeys.lastyear_obtain_marks(), ''),
			FormKeys.annual_income(form=True)						: self.student.get(FormKeys.annual_income(), ''),
			FormKeys.income_cert_app_no(form=True, pre=pre)			: self.student.get(FormKeys.income_cert_app_no(), ''),
			FormKeys.income_cert_no(form=True)						: self.student.get(FormKeys.income_cert_no(), ''),
			FormKeys.income_cert_issue_date(form=True)				: self.student.get(FormKeys.income_cert_issue_date(), ''),
			FormKeys.bank_account_no(form=True)						: self.student.get(FormKeys.bank_account_no(), ''),
			FormKeys.bank_account_no_re(form=True)					: self.student.get(FormKeys.bank_account_no_re(), ''),
			FormKeys.branch_dist_name(form=True)					: self.district.get_code("rampur"),
			FormKeys.bank_name(form=True)							: self.bank.get_code(
				self.student.get(FormKeys.bank_name(), '')),
			FormKeys.branch_name(form=True)							: self.branch.get_code(
				self.student.get(FormKeys.bank_name(), ''), self.student.get(FormKeys.branch_name(), '')),
			FormKeys.bank_account_holder_name(form=True)			: self.student.get(FormKeys.bank_account_holder_name(), ''),
			# FormKeys.aadhaar_no(form = True, pre = pre):				self.student.get(FormKeys.aadhaar_no(),''),
			FormKeys.std(form=True)									: self.course.get_code(
				self.student.get(FormKeys.std(), '')),
			FormKeys.admission_date(form=True, pre=pre)				: self.student.get(FormKeys.admission_date(), ''),
			FormKeys.board_reg_no(form=True)						: self.student.get(FormKeys.board_reg_no(), ''),
			FormKeys.board(form=True)								: self.board.get_code(
				self.student.get(FormKeys.board(), '')),
			FormKeys.previous_school(form=True, pre=pre)			: self.student.get(FormKeys.previous_school(), ''),
			FormKeys.captcha_value(form=True)						: captcha_value,
			FormKeys.check_agree(form=True)							: 'on',
			FormKeys.submit(form=True)								: 'Submit'
		}
		if pre:
			form_data[FormKeys.tc_no(form=True)] = self.student.get(FormKeys.tc_no(), '')
			form_data[FormKeys.tc_date(form=True)] = self.student.get(FormKeys.tc_date(), '')
			form_data[FormKeys.permanent_address_1(form=True)] = self.student.get(
				FormKeys.permanent_address_1(), '') + ' ' + self.student.get(FormKeys.permanent_address_2(), '')
			form_data[FormKeys.income_cert_name(form=True)] = self.student.get(FormKeys.income_cert_name(), '')

		else:
			percentage = str(round(float(self.student.get(FormKeys.lastyear_obtain_marks(), '')) / float(
				self.student.get(FormKeys.lastyear_total_marks(), '')) * 100, 2))
			if (len(percentage)) < 5:
				percentage += '0'
			# form_data[FormKeys.father_aadhaar_no(form = True)]		=	self.student.get(FormKeys.father_aadhaar_no(),'')
			# form_data[FormKeys.mother_aadhaar_no(form = True)]		=	self.student.get(FormKeys.mother_aadhaar_no(),'')
			form_data[FormKeys.permanent_address_1(form=True)] = self.student.get(FormKeys.permanent_address_1(), '')
			form_data[FormKeys.permanent_address_2(form=True)] = self.student.get(FormKeys.permanent_address_2(), '')
			form_data[FormKeys.mailing_address_1(form=True)] = self.student.get(FormKeys.permanent_address_1(), '')
			form_data[FormKeys.mailing_address_2(form=True)] = self.student.get(FormKeys.permanent_address_2(), '')
			form_data[FormKeys.high_school_obtain_marks(form=True)] = self.student.get(
				FormKeys.high_school_obtain_marks(), '')
			form_data[FormKeys.high_school_total_marks(form=True)] = self.student.get(FormKeys.high_school_total_marks(), '')
			form_data[FormKeys.resident_type(form=True)] = '2'
			form_data[FormKeys.total_fees(form=True)] = self.student.get(FormKeys.total_fees(), '')
			form_data[FormKeys.tuition_fees(form=True)] = self.student.get(FormKeys.tuition_fees(), '')
			form_data[FormKeys.total_fees_submitted(form=True)] = self.student.get(FormKeys.total_fees_submitted(), '')
			form_data[FormKeys.fees_receipt_no(form=True)] = self.student.get(FormKeys.fees_receipt_no(), '')
			form_data[FormKeys.fees_receipt_date(form=True)] = self.student.get(FormKeys.fees_receipt_date(), '')
			form_data[FormKeys.total_fees_left(form=True)] = self.student.get(FormKeys.total_fees_left(), '')
			form_data[FormKeys.disability(form=True)] = self.student.get(FormKeys.disability(), '0')
			form_data[FormKeys.lastyear_scholarship_amt(form=True)] = self.student.get(
				FormKeys.lastyear_scholarship_amt(), '')
			form_data[FormKeys.lastyear_std(form=True)] = self.student.get(FormKeys.lastyear_std(), '')
			form_data[FormKeys.lastyear_percentage(form=True)] = percentage
			form_data[FormKeys.address_same(form=True)] = 'on'

		# Only fill caste data if the student is not muslim.
		if self.religion.get_code(self.student.get(FormKeys.religion(), '')) != self.religion.get_code('muslim'):
			form_data[FormKeys.subcaste(form=True)] = self.sub_caste.get_code(self.student.get(FormKeys.subcaste(), ''))
			form_data[FormKeys.caste_cert_issue_date(form=True, pre=pre)] = self.student.get(
				FormKeys.caste_cert_issue_date(), '')
			if pre:
				form_data[FormKeys.caste_cert_name(form=True)] = self.student.get(FormKeys.caste_cert_name(), '')
			form_data[FormKeys.caste_cer_app_no(form=True, pre=pre)] = self.student.get(FormKeys.caste_cer_app_no(), '')
			form_data[FormKeys.caste_cert_no(form=True, pre=pre)] = self.student.get(FormKeys.caste_cert_no(), '')
		return form_data
