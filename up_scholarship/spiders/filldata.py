import urllib.parse as urlparse
import scrapy
from datetime import datetime
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings, StdCategory, FormSets
from up_scholarship.spiders.base import BaseSpider
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
		super().__init__(FillDataSpider, *args, **kwargs)

	def start_requests(self):
		""" Load student's file and get login page if we have some students"""
		self.i_students = self.skip_to_next_valid()
		self.save_if_done(raise_exc=False)
		if self.no_students > 0 and self.no_students != self.i_students:
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def login_form(self, response):
		""" Login the form after getting captcha from previous response.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In login form. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]

			# Get captcha text from our ml model
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta['old_response']

			# Extract hf for password
			hf = response.xpath('//*[@id="' + FormKeys.hf(self.cd.current_form_set) + '"]/@value').extract_first()

			form_data = utl.get_login_form_data(
				student,
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
			url = self.url_provider.get_fill_reg_url(student.get(FormKeys.std(), ''), app_id, self.is_renewal)
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
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]
			form_data = {
				FormKeys.event_target()			: FormKeys.bank_name(form=True),
				FormKeys.bank_name(form=True)	: self.bank.get_code(student.get(FormKeys.bank_name(), ''))
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
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]
			std_c = utl.get_std_category(student.get(FormKeys.std(), ''))
			pre = std_c == StdCategory.pre
			form_data = {
				FormKeys.event_target()							: FormKeys.branch_dist_name(form=True),
				FormKeys.bank_name(form=True)					: self.bank.get_code(
					student.get(FormKeys.bank_name(), '')),
				FormKeys.branch_dist_name(form=True)	: self.district.get_code("rampur")
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
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]
			std_c = utl.get_std_category(student.get(FormKeys.std(), ''))
			pre = std_c == StdCategory.pre
			form_data = {
				FormKeys.event_target()					: FormKeys.branch_name(form=True),
				FormKeys.bank_name(form=True)			: self.bank.get_code(
																student.get(FormKeys.bank_name(), '')),
				FormKeys.branch_dist_name(form=True)	: self.district.get_code("rampur"),
				FormKeys.branch_name(form=True)			: self.branch.get_code(
																student.get(FormKeys.bank_name(), ''),
																student.get(FormKeys.branch_name(), ''))
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
		""" Parse the form to check if the form is really filled.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In Parse. Last URL: %s', response.url)
		student = self.students[self.i_students]
		if response.url.lower().find(TestStrings.app_new_filled.lower()) != -1 or response.url.lower().find(
				TestStrings.app_renew_filled.lower()) != -1:
			student[FormKeys.app_filled()] = 'Y'
			student[FormKeys.status()] = 'Success'
			self.students[self.i_students] = student
			logger.info("----------------Application got filled---------------")
			self.i_students += 1
			self.i_students = self.skip_to_next_valid()
			self.tried = 0
		else:
			self.process_errors(response, [TestStrings.app_fill_form, TestStrings.error])
		self.save_if_done()
		student = self.students[self.i_students]
		url = self.url_provider.get_login_reg_url(student.get(FormKeys.std(), ''), self.is_renewal)
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		logger.info("In Captcha. Last URL " + response.url)
		if self.process_errors(response, [TestStrings.error]):
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
			request = scrapy.Request(url=captcha_url, callback=callback, dont_filter=True, errback=self.errback_next)
			request.meta['old_response'] = response
			yield request

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
			# Set return index if student is not marked for skipping,
			# registration year is current year and application is not filled.
			if student.get(FormKeys.skip(), '') == 'N' and reg_year == datetime.today().year and student.get(
					FormKeys.app_filled(), '') == 'N':
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
		if return_index != -1:
			student = self.students[return_index]
			logger.info('Filling application of: ' + student.get(FormKeys.name(), '') + ' of std: ' + student.get(
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
		std_c = utl.get_std_category(student.get(FormKeys.std(), ''))
		pre = std_c == StdCategory.pre
		form_data = {
			FormKeys.last_year_result(form=True)					: student.get(FormKeys.last_year_result(), 'P'),
			FormKeys.lastyear_total_marks(form=True)				: student.get(FormKeys.lastyear_total_marks(), ''),
			FormKeys.lastyear_obtain_marks(form=True)				: student.get(FormKeys.lastyear_obtain_marks(), ''),
			FormKeys.annual_income(form=True)						: student.get(FormKeys.annual_income(), ''),
			FormKeys.income_cert_app_no(form=True, pre=pre)			: student.get(FormKeys.income_cert_app_no(), ''),
			FormKeys.income_cert_no(form=True)						: student.get(FormKeys.income_cert_no(), ''),
			FormKeys.income_cert_issue_date(form=True)				: student.get(FormKeys.income_cert_issue_date(), ''),
			FormKeys.bank_account_no(form=True)						: student.get(FormKeys.bank_account_no(), ''),
			FormKeys.bank_account_no_re(form=True)					: student.get(FormKeys.bank_account_no_re(), ''),
			FormKeys.branch_dist_name(form=True)					: self.district.get_code("rampur"),
			FormKeys.bank_name(form=True)							: self.bank.get_code(
				student.get(FormKeys.bank_name(), '')),
			FormKeys.branch_name(form=True)				: self.branch.get_code(
				student.get(FormKeys.bank_name(), ''), student.get(FormKeys.branch_name(), '')),
			FormKeys.bank_account_holder_name(form=True)	: student.get(FormKeys.bank_account_holder_name(), ''),
			# FormKeys.aadhaar_no(form = True, pre = pre):				student.get(FormKeys.aadhaar_no(),''),
			FormKeys.std(form=True)									: self.course.get_code(
				student.get(FormKeys.std(), '')),
			FormKeys.admission_date(form=True, pre=pre)				: student.get(FormKeys.admission_date(), ''),
			FormKeys.board_reg_no(form=True)						: student.get(FormKeys.board_reg_no(), ''),
			FormKeys.board(form=True)								: self.board.get_code(
				student.get(FormKeys.board(), '')),
			FormKeys.previous_school(form=True, pre=pre)			: student.get(FormKeys.previous_school(), ''),
			FormKeys.captcha_value(form=True)						: captcha_value,
			FormKeys.check_agree(form=True)							: 'on',
			FormKeys.submit(form=True)								: 'Submit'
		}
		if pre:
			form_data[FormKeys.tc_no(form=True)] = student.get(FormKeys.tc_no(), '')
			form_data[FormKeys.tc_date(form=True)] = student.get(FormKeys.tc_date(), '')
			form_data[FormKeys.permanent_address_1(form=True)] = student.get(
				FormKeys.permanent_address_1(), '') + ' ' + student.get(FormKeys.permanent_address_2(), '')
			form_data[FormKeys.income_cert_name(form=True)] = student.get(FormKeys.income_cert_name(), '')

		else:
			percentage = str(round(float(student.get(FormKeys.lastyear_obtain_marks(), '')) / float(
				student.get(FormKeys.lastyear_total_marks(), '')) * 100, 2))
			if (len(percentage)) < 5:
				percentage += '0'
			# form_data[FormKeys.father_aadhaar_no(form = True)]		=	student.get(FormKeys.father_aadhaar_no(),'')
			# form_data[FormKeys.mother_aadhaar_no(form = True)]		=	student.get(FormKeys.mother_aadhaar_no(),'')
			form_data[FormKeys.permanent_address_1(form=True)] = student.get(FormKeys.permanent_address_1(), '')
			form_data[FormKeys.permanent_address_2(form=True)] = student.get(FormKeys.permanent_address_2(), '')
			form_data[FormKeys.mailing_address_1(form=True)] = student.get(FormKeys.permanent_address_1(), '')
			form_data[FormKeys.mailing_address_2(form=True)] = student.get(FormKeys.permanent_address_2(), '')
			form_data[FormKeys.high_school_obtain_marks(form=True)] = student.get(
				FormKeys.high_school_obtain_marks(), '')
			form_data[FormKeys.high_school_total_marks(form=True)] = student.get(FormKeys.high_school_total_marks(), '')
			form_data[FormKeys.resident_type(form=True)] = '2'
			form_data[FormKeys.total_fees(form=True)] = student.get(FormKeys.total_fees(), '')
			form_data[FormKeys.tuition_fees(form=True)] = student.get(FormKeys.tuition_fees(), '')
			form_data[FormKeys.total_fees_submitted(form=True)] = student.get(FormKeys.total_fees_submitted(), '')
			form_data[FormKeys.fees_receipt_no(form=True)] = student.get(FormKeys.fees_receipt_no(), '')
			form_data[FormKeys.fees_receipt_date(form=True)] = student.get(FormKeys.fees_receipt_date(), '')
			form_data[FormKeys.total_fees_left(form=True)] = student.get(FormKeys.total_fees_left(), '')
			form_data[FormKeys.disability(form=True)] = student.get(FormKeys.disability(), '0')
			form_data[FormKeys.lastyear_scholarship_amt(form=True)] = student.get(
				FormKeys.lastyear_scholarship_amt(), '')
			form_data[FormKeys.lastyear_std(form=True)] = student.get(FormKeys.lastyear_std(), '')
			form_data[FormKeys.lastyear_percentage(form=True)] = percentage
			form_data[FormKeys.address_same(form=True)] = 'on'

		# Only fill caste data if the student is not muslim.
		if self.religion.get_code(student.get(FormKeys.religion(), '')) != self.religion.get_code('muslim'):
			form_data[FormKeys.subcaste(form=True)] = self.sub_caste.get_code(student.get(FormKeys.subcaste(), ''))
			form_data[FormKeys.caste_cert_issue_date(form=True, pre=pre)] = student.get(
				FormKeys.caste_cert_issue_date(), '')
			if pre:
				form_data[FormKeys.caste_cert_name(form=True)] = student.get(FormKeys.caste_cert_name(), '')
			form_data[FormKeys.caste_cer_app_no(form=True, pre=pre)] = student.get(FormKeys.caste_cer_app_no(), '')
			form_data[FormKeys.caste_cert_no(form=True, pre=pre)] = student.get(FormKeys.caste_cert_no(), '')
		return form_data
