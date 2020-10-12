import urllib.parse as urlparse
import scrapy
from datetime import datetime
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings, StdCategory, FormSets
from up_scholarship.spiders.base import BaseSpider, SkipConfig
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class FinalSubmitDataSpider(BaseSpider):
	name = "finalsubmit"
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.reg_no(), FormKeys.dob(), FormKeys.name(), FormKeys.app_filled(),
		FormKeys.photo_uploaded(), FormKeys.father_name(), FormKeys.submitted_for_check(), FormKeys.final_submitted()
	]

	def __init__(self, *args, **kwargs):
		""" Load student"s file and init variables"""
		skip_config = SkipConfig()
		skip_config.common_required_keys = self.common_required_keys
		skip_config.satisfy_criterias = [FormKeys.submitted_for_check()]
		skip_config.disatisfy_criterias = [FormKeys.final_submitted()]
		super().__init__(FinalSubmitDataSpider, skip_config, *args, **kwargs)

	def start_requests(self):
		if self.student:
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def login_form(self, response):
		logger.info("In login form. Last URL: %s", response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta["old_response"]

			# Extract hf for password
			hf = response.xpath("//*[@id='" + FormKeys.hf(self.cd.current_form_set) + "']/@value").extract_first()

			form_data = utl.get_login_form_data(self.student, hf, self.is_renewal, captcha_value, FormKeys(),
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
		logger.info("In accept popup. Last URL: %s", response.url)
		if self.process_errors(response, [TestStrings.error, TestStrings.login]):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		elif response.url.lower().find(TestStrings.app_default) != -1:
			# Extract appid for url
			logger.info("Got default response url %s", response.url)
			everything_fine, status = self.check_if_matched(response,
															self.religion.get_code(self.student[FormKeys.religion()]),
															utl.get_std_category(
																self.student[FormKeys.std()]) == StdCategory.pre)
			if everything_fine:
				parsed = urlparse.urlparse(response.url)
				app_id = urlparse.parse_qs(parsed.query)["Appid"][0]
				std = self.student.get(FormKeys.std(), "")
				if std == "12":
					url = self.url_provider.get_final_print_url(self.student.get(FormKeys.std(), ""), app_id,
																self.is_renewal)
					request = scrapy.Request(url=url, callback=self.save_print, dont_filter=True,
											 errback=self.errback_next)
				else:
					url = self.url_provider.get_final_disclaimer_url(self.student.get(FormKeys.std(), ""), app_id,
																	 self.is_renewal)
					request = scrapy.Request(url=url, callback=self.final_disclaimer, dont_filter=True,
											 errback=self.errback_next)
			# request.meta["old_response"] = response
			else:
				self.student[FormKeys.status()] = status
				self.err_students.append(self.student)
				self.students[self.current_student_index] = self.student
				self.skip_to_next_valid()
				url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
				request = scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True,
										 errback=self.errback_next)
			yield request
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

	def final_disclaimer(self, response):
		logger.info("In Final disclaimer. Last URL: %s", response.url)
		if response.url.lower().find(TestStrings.final_disclaimer.lower()) != -1:
			parsed = urlparse.urlparse(response.url)
			app_id = urlparse.parse_qs(parsed.query)["Appid"][0]

			url = self.url_provider.get_final_print_url(self.student.get(FormKeys.std(), ""), app_id, self.is_renewal)
			request = scrapy.Request(url=url, callback=self.save_print, dont_filter=True, errback=self.errback_next)

		elif response.url.lower().find(TestStrings.final_print) != -1:
			logger.info("Saving student\"s final page")
			utl.save_file_with_name(self.student, response, self.spider_name, str(datetime.today().year),
									extra="/finalprint")

			img_url = response.xpath("//*[@id='PhotoImg']/@src").extract_first()
			parsed = urlparse.urlparse(img_url)
			app_id = urlparse.parse_qs(parsed.query)["App_Id"][0]

			url = self.url_provider.get_img_print_url(self.student.get(FormKeys.std(), ""), app_id, self.is_renewal)
			request = scrapy.Request(url=url, callback=self.save_img, dont_filter=True, errback=self.errback_next)
		else:
			self.process_errors(response, [TestStrings.app_default, TestStrings.error])
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
			request = scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		yield request

	def save_print(self, response):
		logger.info("In save print. Last URL: %s", response.url)
		if response.url.lower().find(TestStrings.final_print) != -1:

			logger.info("Saving student\"s final page")
			utl.save_file_with_name(self.student, response, self.spider_name, str(datetime.today().year),
									extra="/finalprint")

			img_url = response.xpath("//*[@id='PhotoImg']/@src").extract_first()
			parsed = urlparse.urlparse(img_url)
			app_id = urlparse.parse_qs(parsed.query)["App_Id"][0]

			url = self.url_provider.get_img_print_url(self.student.get(FormKeys.std(), ""), app_id, self.is_renewal)
			request = scrapy.Request(url=url, callback=self.save_img, dont_filter=True, errback=self.errback_next)
			# request.meta["old_response"] = response.meta["old_response"]
			yield request
		else:
			self.process_errors(response, [TestStrings.app_default, TestStrings.error])
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def save_img(self, response):
		logger.info("In save img. Last URL: %s", response.url)
		if response.url.lower().find(TestStrings.show_image) != -1:
			parsed = urlparse.urlparse(response.url)
			f = parsed.path.split("/")
			f = f[len(f) - 1]

			logger.info("Saving student\"s image")
			utl.save_file_with_name(self.student, response, self.spider_name, str(datetime.today().year), extension="",
									extra="/" + f)

			self.student[FormKeys.final_submitted()] = "Y"
			self.student[FormKeys.status()] = "Success"
			self.students[self.current_student_index] = self.student
			logger.info("----------------Application got saved for instituion---------------")
			print("----------------Application got saved for instituion---------------")
			self.skip_to_next_valid()
		else:
			self.process_errors(response, [TestStrings.app_default, TestStrings.error])
		url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		print("In Captcha. Last URL: " + response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_login_reg_url(self.student.get(FormKeys.std(), ""), self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_url = self.url_provider.get_captcha_url()
			request = scrapy.Request(url=captcha_url, callback=self.login_form, dont_filter=True,
									 errback=self.errback_next)
			request.meta["old_response"] = response
			yield request

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
		logger.info(
			str(final_form_status) + " " + str(income_cert_no_status) + " " + str(caste_cert_no_status) + " " + str(
				annual_income_status))
		ok = True
		status = ""
		if final_form_status is None or len(final_form_status) < 4:
			if income_cert_no_status is None or str(income_cert_no_status).lower() != TestStrings.matched:
				status += "Income cert no status: " + str(income_cert_no_status) + "; "
				ok = False
			if religion != self.religion.get_code("muslim") and \
				self.student.get(FormKeys.caste()).lower() != "gen" and \
				(caste_cert_no_status is None or str(caste_cert_no_status).lower() != TestStrings.matched):
				status += "Caste cert no status: " + str(caste_cert_no_status) + "; "
				ok = False
			if annual_income_status is None or str(annual_income_status).lower() != TestStrings.matched:
				status += "Annual income status: " + str(annual_income_status) + "; "
				ok = False
			if not pre and (high_school_status is None or str(high_school_status).lower() != TestStrings.matched):
				status += "High school status: " + str(high_school_status) + "; "
				ok = False
		else:
			ok = False
			status = final_form_status
		if ok:
			status = "Success"
		print(status)
		return ok, status

	def get_status(self, response, key: str):
		return response.xpath("//*[@id='" + key + "']").xpath("normalize-space()").extract_first()
