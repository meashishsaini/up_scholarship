import urllib.parse as urlparse
import scrapy
from datetime import datetime
import mimetypes
import io
import codecs
from pathlib import Path
from scrapy.http import Request
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings, StdCategory, FormSets
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.spiders.base import BaseSpider, SkipConfig
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class UploadPhotoSpider(BaseSpider):
	name = "uploadphoto"
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.reg_no(), FormKeys.dob(), FormKeys.name(), FormKeys.app_filled(),
		FormKeys.photo_uploaded(), FormKeys.father_name()]

	def __init__(self, *args, **kwargs):
		""" Load student"s file and init variables"""
		skip_config = SkipConfig()
		skip_config.common_required_keys = self.common_required_keys
		skip_config.disatisfy_criterias = [FormKeys.photo_uploaded()]
		skip_config.satisfy_criterias = [FormKeys.app_filled()]
		super().__init__(UploadPhotoSpider, skip_config, *args, **kwargs)

	def start_requests(self):
		if self.student:
			url = self.url_provider.get_login_reg_url(self.student[FormKeys.std()], self.is_renewal)
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

			url = self.url_provider.get_photo_up_url(self.student.get(FormKeys.std(), ""), app_id, self.is_renewal)
			logger.info("URL: %s", url)
			yield scrapy.Request(url=url, callback=self.upload_photo, dont_filter=True, errback=self.errback_next)
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

	def upload_photo(self, response):
		logger.info("In upload photo. Last URL: %s", response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			url = self.url_provider.get_login_reg_url(self.student[FormKeys.std()], self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			headers = response.request.headers

			parsed = urlparse.urlparse(response.url)
			app_id = urlparse.parse_qs(parsed.query)["Appid"][0]
			url = self.url_provider.get_photo_up_url(self.student.get(FormKeys.std(), ""), app_id, self.is_renewal)

			viewstate = response.xpath("//*[@id='" + FormKeys.view_state() + "']/@value").extract_first()
			viewstategenerater = response.xpath \
				("//*[@id='" + FormKeys.view_state_generator() + "']/@value").extract_first()
			eventvalidation = response.xpath("//*[@id='" + FormKeys.event_validation() + "']/@value").extract_first()

			filename = utl.get_photo_by_uid_name(self.cd.data_dir, self.student, "jpg ", self.student[FormKeys.reg_year()], FormKeys())
			if utl.check_if_file_exists(filename):
				pre = utl.get_std_category(self.student[FormKeys.std()]) == StdCategory.pre

				fields = [(FormKeys.view_state(), viewstate),
						(FormKeys.view_state_generator(), viewstategenerater),
						(FormKeys.view_state_encrypted(), ""),
						(FormKeys.event_validation(), eventvalidation),
						(FormKeys.upload_photo(self.cd.current_form_set, form=True),
							"Upload Photo")]
				if not pre:
					fields.append((FormKeys.is_pic_upload(), "Y"))
					fields.append((FormKeys.is_handi_upload(), ""))
					fields.append((FormKeys.handi_type(), "0"))

				files = [(FormKeys.upload_photo_name(form=True), self.student[FormKeys.aadhaar_no()] + ".jpg", open(filename, "rb"))]
				logger.info("Photo file %s", files)
				logger.info("Photo fields %s", fields)
				content_type, body = utl.MultipartFormDataEncoder().encode(fields, files)
				headers["Content-Type"] = content_type
				headers["Content-length"] = str(len(body))

				request_with_cookies = Request(url=url, method="POST", headers=headers, body=body, dont_filter=True)
				yield request_with_cookies
			else:
				self.student[FormKeys.status()] = "Photo file not found"
				self.students[self.current_student_index] = self.student
				self.skip_to_next_valid()
				url = self.url_provider.get_login_reg_url(self.student[FormKeys.std()], self.is_renewal)
				yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def parse(self, response):
		logger.info("Parse Got URL: %s", response.url)
		upload_status = ""
		scripts = response.xpath("//script/text()").extract()
		for script in scripts:
			if len(script) > 10 and script.lower().find(TestStrings.alert) != -1:
				upload_status = script[7:-1]
				break
		if upload_status.lower().find(TestStrings.photo_uploaded) != -1:
			self.student[FormKeys.photo_uploaded()] = "Y"
			self.student[FormKeys.status()] = "Success"
			self.students[self.current_student_index] = self.student
			logger.info("----------------Photo successfully uploaded---------------")
			print("----------------Photo successfully uploaded---------------")
			self.skip_to_next_valid()
		else:
			self.process_errors(response, [TestStrings.photo_upload, TestStrings.error])
		url = self.url_provider.get_login_reg_url(self.student[FormKeys.std()], self.is_renewal)
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		print("In Captcha: " + response.url)
		if self.process_errors(response, [TestStrings.error]):
			url = self.url_provider.get_login_reg_url(self.student[FormKeys.std()], self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_url = self.url_provider.get_captcha_url()
			if response.url.lower().find(TestStrings.login) != -1:
				request = scrapy.Request(url=captcha_url, callback=self.login_form, dont_filter=True,
										 errback=self.errback_next)
			else:
				request = scrapy.Request(url=captcha_url, callback=self.upload_photo, dont_filter=True,
										 errback=self.errback_next)
			request.meta["old_response"] = response
			yield request