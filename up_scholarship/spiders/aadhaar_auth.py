import urllib.parse as urlparse
import scrapy
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings, StdCategory
from up_scholarship.spiders.base import BaseSpider, SkipConfig
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class AadhaarAuthSpider(BaseSpider):
	name = "aadhaarauth"
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.reg_no(), FormKeys.dob(), FormKeys.name(), FormKeys.app_filled(),
		FormKeys.photo_uploaded(), FormKeys.father_name(), FormKeys.submitted_for_check(), FormKeys.aadhaar_authenticated()
	]

	def __init__(self, *args, **kwargs):
		""" Load student"s file and init variables"""
		skip_config = SkipConfig()
		skip_config.common_required_keys = self.common_required_keys
		skip_config.satisfy_criterias = [FormKeys.photo_uploaded()]
		skip_config.disatisfy_criterias = [FormKeys.aadhaar_authenticated()]
		super().__init__(AadhaarAuthSpider, skip_config, *args, **kwargs)

	def start_requests(self):
		if self.student:
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def login_form(self, response):
		logger.info("In login form. Last Url: %s", response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			url = self.url_provider.get_login_reg_url(self.student[FormKeys.std()], self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta["old_response"]

			# Extract hf for password
			hf = response.xpath("//*[@id='" + FormKeys.hf(self.cd.current_form_set) + "']/@value").extract_first()

			form_data = utl.get_login_form_data(self.student, hf, self.is_renewal, captcha_value, FormKeys(), self.cd.current_form_set)
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
		logger.info("In accept popup. Last URL: %s", response.url)
		if self.process_errors(response, [TestStrings.error, TestStrings.login]):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		# Got default response, means popup has been accepted.
		elif response.url.lower().find(TestStrings.app_default) != -1:
			logger.info("Got default response url %s", response.url)
			# Extract appid for url
			parsed = urlparse.urlparse(response.url)
			app_id = urlparse.parse_qs(parsed.query)["Appid"][0]

			url = self.url_provider.get_aadhaar_auth_url(self.student.get(FormKeys.std(), ""), app_id, self.is_renewal)
			logger.info("URL: %s", url)
			request = scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
			request.meta["old_response"] = response
			yield request
		# Popup might not have been accepted, accept it
		else:
			logger.info("Accepting popup. Last URL: %s", response.url)
			request = scrapy.FormRequest.from_response(
				response,
				formdata={
					FormKeys.check_popup_agree(form=True)	: "on",
					FormKeys.popup_button(form=True)		: "Proceed >>>",
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
		logger.info("In fill data. Last URL: %s", response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta["old_response"]
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
		logger.info("In parse. Last URL: %s", response.url)
		correct_label = response.xpath(
			"//*[@id='" + FormKeys.correct_lbl() + "']/text()").extract_first()
		logger.info("Correct label: %s", correct_label)
		correct_label = correct_label if correct_label else ""
		if response.url.lower().find(TestStrings.app_default) == -1 and correct_label == TestStrings.aadhaar_authenticated:
			self.student[FormKeys.aadhaar_authenticated()] = "Y"
			# Std 9 and does not require OTP verification
			if utl.get_std_category(self.student.get(FormKeys.std())) == StdCategory.pre:
				self.student[FormKeys.aadhaar_otp_authenticated()] = "Y"
			self.student[FormKeys.status()] = "Success"
			self.students[self.current_student_index] = self.student
			logger.info("----------------Aadhaar got authenticated---------------")
			print("----------------Aadhaar got authenticated---------------")
			self.skip_to_next_valid()
		else:
			self.process_errors(response, [TestStrings.app_default, TestStrings.aadhaar_auth, TestStrings.error])
		url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		logger.info("In Captcha. Last URL: " + response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
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
			request.meta["old_response"] = response
			yield request

	def get_fill_form_data(self, student: dict, captcha_value: str) -> dict:
		""" Create and return the form data
			Keyword arguments:
			student -- student whose details needed to be filled.
			captcha_value -- captcha value to be used in filling form.
			Returns: dict
		"""
		enrypted_aadhaar_no = utl.get_encryped_aadhaar(self.student.get(FormKeys.aadhaar_no(),""))
		form_data = {
			FormKeys.aadhaar_no(form = True)		:	enrypted_aadhaar_no,
			FormKeys.aadhaar_no_re(form = True)		:	enrypted_aadhaar_no,
			FormKeys.captcha_value(form=True)		:	captcha_value,
			FormKeys.check_agree(form=True)			:	"on",
			FormKeys.submit(form=True)				:	"Verify Aadhar"
		}
		return form_data
