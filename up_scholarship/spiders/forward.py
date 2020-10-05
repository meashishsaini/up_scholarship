import scrapy
from datetime import datetime
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings, FormSets, StdCategory
from up_scholarship.spiders.base import BaseSpider, SkipConfig
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class ForwardAppSpider(BaseSpider):
	name = "forward"
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.name(), FormKeys.institute(), FormKeys.final_submitted(),
		FormKeys.reg_year(), FormKeys.app_received(), FormKeys.religion(), FormKeys.app_verified(), FormKeys.app_forwarded()]
	school_type = "R"	# our school type

	def __init__(self, *args, **kwargs):
		""" Load student"s file and init variables"""
		skip_config = SkipConfig()
		skip_config.common_required_keys = self.common_required_keys
		skip_config.disatisfy_criterias = [FormKeys.app_forwarded()]
		skip_config.satisfy_criterias = [FormKeys.app_verified()]
		super().__init__(ForwardAppSpider, skip_config, *args, **kwargs)
		self.cd.current_form_set = FormSets.two

	# self.board = CodeFileReader(self.cd.board_file)

	def start_requests(self):
		""" Get institute login page"""
		if self.student:
			url = self.url_provider.get_institute_login_url(self.student.get(FormKeys.std(), ""))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)

	def get_district(self, response):
		""" Fill the school district.
				Keyword arguments:
				response -- previous scrapy response.
		"""
		logger.info("In get school. Last URL: %s", response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_institute_login_url(self.student.get(FormKeys.std(), ""))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			std_category = utl.get_std_category(self.student.get(FormKeys.std()))
			form_data = {
				FormKeys.event_target()					: FormKeys.institute_login_type_radio_button(std_category=std_category),
				FormKeys.district(form=True)			: self.district.get_code("rampur"),
				FormKeys.institute_login_type_radio_button(form=True): FormKeys.institute_login_radio_button_value(std_category=std_category),
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
		logger.info("In login form. Last URL: %s", response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			url = self.url_provider.get_institute_login_url(self.student.get(FormKeys.std(), ""))
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			# Get captcha text from our ml model
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta["old_response"]

			hf = response.xpath("//*[@id='" + FormKeys.hf() + "']/@value").extract_first()

			form_data = utl.get_login_institute_data(
				self.student,
				captcha_value,
				hf,
				self.district,
				self.institute)
			logger.info("Login form data: %s", form_data)
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.forward_app,
				errback=self.errback_next,
				dont_filter=True
			)
			yield request

	def forward_app(self, response):
		""" Open the verify application page
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info("In forward_app. Last URL: %s", response.url)
		if self.process_errors(response, [TestStrings.error]) or \
			response.url.lower().find(TestStrings.institute_login_success.lower()) == -1:
			url = self.url_provider.get_institute_login_url(self.student.get(FormKeys.std(), ""))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			url = self.url_provider.get_institute_forward_url(self.student.get(FormKeys.std(), ""))
			yield scrapy.Request(
				url=url, callback=self.search_application_number, dont_filter=True, errback=self.errback_next)

	def search_application_number(self, response):
		""" Search the application number.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info("In search_application_number. Last URL: %s", response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_institute_login_url(self.student.get(FormKeys.std(), ""))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			app_type = "1" if self.is_renewal else "0"
			form_data = {
				FormKeys.application_type(form=True)			: app_type,
				FormKeys.registration_number_search(form=True)	: self.student.get(FormKeys.reg_no(), ""),
				FormKeys.search_button(form=True)				: FormKeys.search_button()
			}
			logger.info("Search form data: %s", form_data)
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.forward,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def forward(self, response):
		""" Select forward from drop down.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info("In forward. Last URL: %s", response.url)
		std_category = utl.get_std_category(self.student.get(FormKeys.std()))
		app_id = response.xpath("//*[@id='%s']//text()" % FormKeys.first_forward_app_id(std_category))
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_institute_login_url(self.student.get(FormKeys.std(), ""))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		elif not app_id and app_id.extract_first() != self.student[FormKeys.reg_no()]:
			message = "Application registration number not found."
			logger.info("Application status: %s", message)
			self.student[FormKeys.status()] = message
			self.students[self.current_student_index] = self.student
			self.skip_to_next_valid()
			url = self.url_provider.get_institute_forward_url(self.student.get(FormKeys.std(), ""))
			yield scrapy.Request(
				url=url, callback=self.search_application_number, dont_filter=True, errback=self.errback_next)
		else:
			form_data = {
				FormKeys.application_forward_marks_total(std_category): self.student.get(FormKeys.lastyear_total_marks()),
				FormKeys.application_forward_marks_obtained(std_category): self.student.get(FormKeys.lastyear_obtain_marks()),
				FormKeys.application_forward_attendance(std_category): "75",
				FormKeys.application_forward_agree(form=True, std_category=std_category): FormKeys.application_forward_agree(),
				FormKeys.application_forward_button(form=True): FormKeys.application_forward_button()
			}
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
		""" Check if application is verified.
					Keyword arguments:
					response -- previous scrapy response.
		"""
		logger.info("In parse. Last URL: %s", response.url)
		utl.save_file_with_name(self.student, response, self.spider_name, str(datetime.today().year), is_debug=True, extra="forward")
		scripts = response.xpath("//script/text()").extract()
		application_forwarded = scripts and scripts[0].find(TestStrings.application_forwarded) != -1
		if not application_forwarded and self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_institute_login_url(self.student.get(FormKeys.std(), ""))
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)
		else:
			if application_forwarded:
				message = "Application successfully forwarded.."
				self.student[FormKeys.status()] = message
				self.student[FormKeys.app_forwarded()] = "Y"
				logger.info("----------------Application got forwarded---------------")
			else:
				message = "Unable to forward application."
				self.student[FormKeys.status()] = message
				self.student[FormKeys.app_forwarded()] = "N"
			logger.info("Application status: %s", message)
			self.students[self.current_student_index] = self.student
			self.skip_to_next_valid()
			url = self.url_provider.get_institute_forward_url(self.student.get(FormKeys.std(), ""))
			yield scrapy.Request(
					url=url, callback=self.search_application_number, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		logger.info("In Captcha. Last URL " + response.url)
		if self.process_errors(response, [TestStrings.error], html=True):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			# Use different callbacks for login form and fill data form.
			captcha_url = self.url_provider.get_captcha_url()
			callback = self.login_form
			request = scrapy.Request(url=captcha_url, callback=callback, dont_filter=True, errback=self.errback_next)
			request.meta["old_response"] = response
			yield request

