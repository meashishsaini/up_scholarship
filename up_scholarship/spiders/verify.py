import scrapy
from datetime import datetime
import logging

from up_scholarship.providers.constants import  FormKeys, TestStrings, FormSets, StdCategory
from up_scholarship.spiders.base import BaseSpider
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class VerifyAppSpider(BaseSpider):
	name = 'verify'
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.name(), FormKeys.institute(), FormKeys.final_submitted(),
		FormKeys.reg_year(), FormKeys.app_received(), FormKeys.religion(), FormKeys.app_verified()]
	school_type = "R"  # our school type

	def __init__(self, *args, **kwargs):
		""" Load student's file and init variables"""
		super().__init__(VerifyAppSpider, *args, **kwargs)

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
		logger.info('In get school. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error]):
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
		logger.info('In get school. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error]):
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
		logger.info('In login form. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
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
				callback=self.verify_page,
				errback=self.errback_next,
				dont_filter=True
			)
			yield request

	def verify_page(self, response):
		""" Open the verify application page
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In verify_page. Last URL: %s', response.url)
		student = self.students[self.i_students]
		if self.process_errors(response, [TestStrings.error]) or \
			response.url.lower().find(TestStrings.institute_login_success.lower()) == -1:
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			url = self.url_provider.get_institute_verify_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(
				url=url, callback=self.search_application_number, dont_filter=True, errback=self.errback_next)

	def search_application_number(self, response):
		""" Search the application number.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In search_application_number. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error]):
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
				callback=self.verify,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def verify(self, response):
		""" Select verify from drop down.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In verify. Last URL: %s', response.url)
		student = self.students[self.i_students]
		app_id = response.xpath('//*[@id="%s"]//text()' % FormKeys.first_app_id())
		if self.process_errors(response, [TestStrings.error]):
			student = self.students[self.i_students]
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		elif not app_id and app_id.extract_first() != student[FormKeys.reg_no()]:
			message = "Application registration number not found."
			logger.info(message)
			student[FormKeys.status()] = message
			self.students[self.i_students] = student
			self.i_students = self.i_students + 1
			self.i_students = self.skip_to_next_valid()
			self.save_if_done()
			url = self.url_provider.get_institute_verify_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(
				url=url, callback=self.search_application_number, dont_filter=True, errback=self.errback_next)
		else:
			form_data = {
				FormKeys.application_verify_status(form=True):	FormKeys.application_verify_status()
			}
			print(form_data)
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.submit_verify_application,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def submit_verify_application(self, response):
		""" Verify application if found.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		student = self.students[self.i_students]
		utl.save_file_with_name(student, response, self.spider_name, str(datetime.today().year), is_debug=True, extra="verify")
		if self.process_errors(response, [TestStrings.error]):
			student = self.students[self.i_students]
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			form_data = {
				FormKeys.event_target(): FormKeys.application_verify_link_button()
			}
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.parse,
				errback=self.errback_next,
				dont_filter=True
			)
			print(form_data)
			yield request

	def parse(self, response):
		""" Check if application is verified.
					Keyword arguments:
					response -- previous scrapy response.
		"""
		logger.info('In parse. Last URL: %s', response.url)
		scripts = response.xpath('//script/text()').extract()
		application_verified = scripts and scripts[0].find(TestStrings.application_verified) != -1
		if not application_verified and self.process_errors(response, [TestStrings.error]):
			student = self.students[self.i_students]
			url = self.url_provider.get_institute_login_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]
			if application_verified:
				message = "Application successfully verified.."
				student[FormKeys.status()] = message
				student[FormKeys.app_verified()] = "Y"
			else:
				message = "Unable to verify application."
				student[FormKeys.status()] = message
				student[FormKeys.app_verified()] = "N"
			logger.info(message)
			self.students[self.i_students] = student
			self.i_students = self.i_students + 1
			self.i_students = self.skip_to_next_valid()
			self.save_if_done()
			url = self.url_provider.get_institute_verify_url(student.get(FormKeys.std(), ''))
			yield scrapy.Request(
					url=url, callback=self.search_application_number, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		logger.info("In Captcha. Last URL " + response.url)
		if self.process_errors(response, [TestStrings.error]):
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
				FormKeys.final_submitted(), '') == 'Y' and student.get(FormKeys.app_received(), '') == 'Y'\
				and student.get(FormKeys.app_verified(), '') == 'N':
				return_index = x
				# Also set the different sets of link used by up scholarship website.
				if utl.get_std_category(student[FormKeys.std()]) == StdCategory.pre:
					self.cd.set_form_set(FormSets.one)
				else:
					self.cd.set_form_set(FormSets.two)
				# If we have old registration no. in student's list set it to renewal.
				self.is_renewal = student.get(FormKeys.old_reg_no(), '') != ''
				if self.is_renewal:
					logger.info('Application is renewal')
				break
		# If return index is not -1 return it or else return total no. of students.
		if return_index != -1:
			student = self.students[return_index]
			logger.info(
				'Verifying application of: ' + student.get(FormKeys.name(), '') + ' of std: ' + student.get(
					FormKeys.std(), ''))
			return return_index
		else:
			return self.no_students

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
