from datetime import datetime
import scrapy
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings, StdCategory, FormSets
from up_scholarship.spiders.base import BaseSpider, SkipConfig
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class RegisterSpider(BaseSpider):
	name = "register"
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.name(), FormKeys.dob(), FormKeys.district(), FormKeys.institute(),
		FormKeys.caste(), FormKeys.father_name(), FormKeys.mother_name(), FormKeys.gender(), FormKeys.board()]
	pre_required_keys = [FormKeys.eight_passing_year(), FormKeys.eight_school()]
	post_required_keys = [FormKeys.high_school_passing_year(), FormKeys.high_school_roll_no(), FormKeys.high_school_name_address()]

	def __init__(self, *args, **kwargs):
		""" Load student"s file and init variables"""
		skip_config = SkipConfig()
		skip_config.common_required_keys = self.common_required_keys
		skip_config.pre_required_keys = self.pre_required_keys
		skip_config.post_required_keys = self.post_required_keys
		skip_config.check_valid_year = False
		super().__init__(RegisterSpider, skip_config, *args, **kwargs)

	def start_requests(self):
		""" Get registration page if we have some students"""
		if self.student:
			url = self.url_provider.get_reg_url(self.student[FormKeys.caste()], self.student[FormKeys.std()], self.student[FormKeys.is_minority()] == "Y")
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)

	def get_district(self, response):
		logger.info("In getting district. Last Url: %s", response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_reg_url(self.student[FormKeys.caste()], self.student[FormKeys.std()], self.student[FormKeys.is_minority()] == "Y")
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True)
		else:
			form_data = {
				FormKeys.event_target()			: FormKeys.district(form=True),
				FormKeys.district(form=True)	: self.district.get_code(self.student[FormKeys.district()])
			}
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.get_institute,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def get_institute(self, response):
		logger.info("In getting institute. Last Url: %s", response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_reg_url(self.student[FormKeys.caste()], self.student[FormKeys.std()], self.student[FormKeys.is_minority()] == "Y")
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True)
		else:
			form_data = {
				FormKeys.event_target()			: FormKeys.institute(form=True),
				FormKeys.district(form=True)	: self.district.get_code(self.student[FormKeys.district()]),
				FormKeys.institute(form=True)	: self.institute.get_code(self.student[FormKeys.institute()])
			}
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.get_caste,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def get_caste(self, response):
		logger.info("In get caste. Last Url: %s", response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_reg_url(self.student[FormKeys.caste()], self.student[FormKeys.std()], self.student[FormKeys.is_minority()] == "Y")
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True)
		else:
			form_data = {
				FormKeys.event_target()			: FormKeys.caste(form=True),
				FormKeys.district(form=True)	: self.district.get_code(self.student[FormKeys.district()]),
				FormKeys.institute(form=True)	: self.institute.get_code(self.student[FormKeys.institute()]),
			}
			if self.student[FormKeys.is_minority()] == "Y":
				form_data[FormKeys.caste(form=True)] = self.caste.get_code("min")
			else:
				form_data[FormKeys.caste(form=True)] = self.caste.get_code(self.student[FormKeys.caste()])
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.get_captcha,
				errback=self.errback_next,
				dont_filter=True,
				dont_click=True
			)
			yield request

	def fill_reg(self, response):
		logger.info("In reg form. Last Url: %s", response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			url = self.url_provider.get_reg_url(self.student[FormKeys.caste()], self.student[FormKeys.std()], self.student[FormKeys.is_minority()] == "Y")
			yield scrapy.Request(url=url, callback=self.get_institute, dont_filter=True)
		else:
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta["old_response"]

			form_data, password = self.get_form_data(captcha_value)
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.parse,
				errback=self.errback_next,
				dont_filter=True
			)
			request.meta["password"] = password
			yield request

	def parse(self, response):
		logger.info("In parse. Last URL: %s ", response.url)
		if response.url.find(TestStrings.registration_success) != -1:
			reg_no = response.xpath("//*[@id='" + FormKeys.reg_no(form=True, reg=True) + "']/text()").extract_first()
			self.student[FormKeys.reg_no()] = reg_no
			self.student[FormKeys.password()] = response.meta["password"]
			self.student[FormKeys.status()] = "Success"
			self.student[FormKeys.reg_year()] = str(datetime.today().year)
			self.students[self.current_student_index] = self.student
			logger.info("----------------Application got registered---------------")
			logger.info("Reg no.: %s password: %s", reg_no, response.meta["password"])
			utl.save_file_with_name(self.student, response, self.spider_name, str(datetime.today().year))
			self.skip_to_next_valid()
		else:
			self.process_errors(response, [TestStrings.registration_form, TestStrings.error])
		url = self.url_provider.get_reg_url(self.student[FormKeys.caste()], self.student[FormKeys.std()], self.student[FormKeys.is_minority()] == "Y")
		yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		print("In Captcha. Last URL: " + response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_reg_url(self.student[FormKeys.caste()], self.student[FormKeys.std()], self.student[FormKeys.is_minority()] == "Y")
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_url = self.url_provider.get_captcha_url()
			request = scrapy.Request(url=captcha_url, callback=self.fill_reg, dont_filter=True,
									 errback=self.errback_next)
			request.meta["old_response"] = response
			yield request

	def get_form_data(self, captcha_value):
		father_husband_name = ""
		if self.student[FormKeys.father_name()] != "":
			father_husband_name = self.student[FormKeys.father_name()]
		else:
			father_husband_name = self.student[FormKeys.husband_name()]
		password = utl.get_random_password()
		hashed_password, _ = utl.get_login_form_password(password)
		form_data = {
			FormKeys.district(form=True)			: self.district.get_code(self.student[FormKeys.district()]),
			FormKeys.institute(form=True)			: self.institute.get_code(self.student[FormKeys.institute()]),
			FormKeys.religion(form=True)			: self.religion.get_code(self.student[FormKeys.religion()]),
			FormKeys.name(form=True)				: self.student[FormKeys.name()],
			FormKeys.father_name(form=True)			: father_husband_name,
			FormKeys.mother_name(form=True)			: self.student[FormKeys.mother_name()],
			FormKeys.dob(form=True, reg=True)		: self.student[FormKeys.dob()],
			FormKeys.gender(form=True)				: self.student[FormKeys.gender()],
			FormKeys.board(form=True)				: self.board.get_code(self.student[FormKeys.board()]),
			FormKeys.mobile_no(form=True, reg=True)	: self.student[FormKeys.mobile_no()],
			FormKeys.password(form=True)			: hashed_password,
			FormKeys.confirm_password(form=True)	: hashed_password,
			FormKeys.captcha_value(form=True)		: captcha_value,
			FormKeys.submit(form=True)				: "Submit",
		}
		if self.student[FormKeys.is_minority()] == "Y":
			form_data[FormKeys.caste(form=True)] = self.caste.get_code("min")
		else:
			form_data[FormKeys.caste(form=True)] = self.caste.get_code(self.student[FormKeys.caste()])
		if utl.get_std_category(self.student[FormKeys().std()]) == StdCategory.pre:
			form_data[FormKeys.eight_passing_year(form=True)] = self.student[FormKeys.eight_passing_year()]
			form_data[FormKeys.eight_school(form=True)] = self.student[FormKeys.eight_school()]

		else:
			form_data[FormKeys.high_school_passing_year(form=True)] = self.student[FormKeys.high_school_passing_year()]
			form_data[FormKeys.high_school_roll_no(form=True)] = self.student[FormKeys.high_school_roll_no()]
			form_data[FormKeys.high_school_name_address(form=True)] = self.student[FormKeys.high_school_name_address()]
		return form_data, password
