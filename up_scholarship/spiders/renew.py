import scrapy
from datetime import datetime
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings
from up_scholarship.spiders.base import BaseSpider, SkipConfig
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class RenewSpider(BaseSpider):
	name = "renew"
	no_students = 0
	common_required_keys = [FormKeys.reg_year(), FormKeys.skip(), FormKeys.std(), FormKeys.name(), FormKeys.reg_no(),
																		FormKeys.dob(), FormKeys.mobile_no()]

	def __init__(self, *args, **kwargs):
		""" Load student"s file and init variables"""
		skip_config = SkipConfig()
		skip_config.common_required_keys = self.common_required_keys
		skip_config.allow_renew = True
		super().__init__(RenewSpider, skip_config, *args, **kwargs)

	def start_requests(self):
		if self.student:
			url = self.url_provider.get_renew_url(self.student[FormKeys.caste()], self.student[FormKeys.std()], self.student[FormKeys.is_minority()] == "Y")
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def fill_form(self, response):
		logger.info("In fill form. Last URL: %s", response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			url = self.url_provider.get_renew_url(self.student[FormKeys.caste()], self.student[FormKeys.std()], self.student[FormKeys.is_minority()] == "Y")
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True)
		else:
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta["old_response"]
			form_data = {
				FormKeys.reg_no(form=True): self.student[FormKeys.reg_no()],
				FormKeys.dob(form=True): self.student[FormKeys.dob()],
				FormKeys.mobile_no(form=True): self.student.get(FormKeys.mobile_no(), ""),
				FormKeys.captcha_value(form=True): captcha_value,
				FormKeys.login(form=True): "Submit",

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
		logger.info("In parse. Previous URL: %s", response.url)
		if response.url.find(TestStrings.renew_success) != -1:
			new_reg_no = response.xpath(
				"//*[@id='" + FormKeys.reg_no(form=True, reg=True) + "']/text()").extract_first()
			vf_code = response.xpath("//*[@id='" + FormKeys.password(form=True, reg=True) + "']/text()").extract_first()
			logger.info("----------------Application got renewed---------------")
			logger.info("New reg no.: %s vf_code: %s", new_reg_no, vf_code)
			print("----------------Application got renewed---------------")
			print("New reg no.:" + new_reg_no)
			src = utl.get_photo_by_uid_name(self.cd.data_dir, self.student, "jpg ", self.student[FormKeys.reg_year()], FormKeys())
			self.student[FormKeys.old_reg_no()] = self.student[FormKeys.reg_no()]
			self.student[FormKeys.reg_no()] = new_reg_no
			self.student[FormKeys.password()] = vf_code
			self.student[FormKeys.status()] = "Success"
			self.student[FormKeys.std()] = str(int(self.student[FormKeys.std()]) + 1)
			#self.student[FormKeys.previous_school()] = self.student[FormKeys.institute()]
			self.student[FormKeys.reg_year()] = str(datetime.today().year)
			self.student = self.remove_old_values(self.student)
			dest = utl.get_photo_by_uid_name(
				self.cd.data_dir, self.student, "jpg ", self.student[FormKeys.reg_year()], FormKeys())
			try:
				utl.copy_file(src, dest)
			except Exception as err:
				print(err)
			self.students[self.current_student_index] = self.student
			utl.save_file_with_name(self.student, response, self.spider_name, str(datetime.today().year))
			self.skip_to_next_valid()
		else:
			self.process_errors(response, [TestStrings.renew_form, TestStrings.error, TestStrings.registration_new])
		url = self.url_provider.get_renew_url(self.student[FormKeys.caste()], self.student[FormKeys.std()], self.student[FormKeys.is_minority()] == "Y")
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		logger.info("In Captcha. Last URL %s", response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_renew_url(self.student[FormKeys.caste()], self.student[FormKeys.std()], self.student[FormKeys.is_minority()] == "Y")
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_url = self.url_provider.get_captcha_url()

			request = scrapy.Request(url=captcha_url, callback=self.fill_form, dont_filter=True, errback=self.errback_next)
			request.meta["old_response"] = response
			yield request

	def remove_old_values(self, student: dict) -> dict:
		# self.student[FormKeys.lastyear_std()] = ""
		# self.student[FormKeys.last_year_result()] = ""
		# self.student[FormKeys.lastyear_total_marks()] = ""
		# self.student[FormKeys.lastyear_obtain_marks()] = ""
		# self.student[FormKeys.admission_date()] = ""
		# self.student[FormKeys.tuition_fees()] = ""
		# self.student[FormKeys.lastyear_scholarship_amt()] = ""
		# self.student[FormKeys.fees_receipt_no()] = ""
		# self.student[FormKeys.total_fees_left()] = ""
		# self.student[FormKeys.total_fees_submitted()] = ""
		# self.student[FormKeys.total_fees()] = ""
		# self.student[FormKeys.fees_receipt_date()] = ""
		# self.student[FormKeys.board_reg_no()] = ""
		# self.student[FormKeys.institute()] = ""
		self.student[FormKeys.app_filled()] = "N"
		self.student[FormKeys.photo_uploaded()] = "N"
		self.student[FormKeys.submitted_for_check()] = "N"
		self.student[FormKeys.final_submitted()] = "N"
		self.student[FormKeys.final_printed()] = "N"
		self.student[FormKeys.app_received()] = "N"
		self.student[FormKeys.app_verified()] = "N"
		self.student[FormKeys.app_forwarded()] = "N"
		return student
