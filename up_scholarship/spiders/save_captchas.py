import urllib.parse as urlparse
import scrapy
from datetime import datetime
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings
from up_scholarship.spiders.base import BaseSpider, SkipConfig
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers import utilities as utl
import os

logger = logging.getLogger(__name__)
MAX_CAPTCHAS_DOWNLOAD = 1000

class SaveCatpchasSpider(BaseSpider):
	"""	UP scholarship captcha downloader spider.
	"""
	name = 'savecaptchas'

	def __init__(self, *args, **kwargs):
		""" Load student's file and init variables"""
		skip_config = SkipConfig()
		super().__init__(SaveCatpchasSpider, skip_config, auto_skip=False, *args, **kwargs)
		self.student = {FormKeys.name(): "Test", FormKeys.reg_no(): "050138191000044",
		FormKeys.password(): "Test@123", FormKeys.reg_year(): "2020", FormKeys.dob(): "05/05/2000",
		FormKeys.std(): "9", FormKeys.mother_name(): "Test", FormKeys.father_name(): "Test"}
		self.current_count = 0
		self.current_captcha = None
		self.current_captcha_value = None

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

			self.current_captcha = response.body
			self.current_captcha_value = captcha_value

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
				callback=self.parse,
				errback=self.errback_next,
				dont_filter=True
			)
			yield request


	def parse(self, response):
		""" Parse the form to check if captcha was correct.
			Keyword arguments:
			response -- previous scrapy response.
		"""
		logger.info('In Parse. Last URL: %s', response.url)
		if response.url.lower().find("popup") != -1:
			filename = "up_scholarship/out/catpchas/" + self.current_captcha_value + ".jpg"
		else:
			filename = "up_scholarship/out/catpchas/wrong/" + self.current_captcha_value + ".jpg"
			self.process_errors(response, [TestStrings.app_fill_form, TestStrings.error])
		os.makedirs(os.path.dirname(filename), exist_ok=True)
		with open(filename, 'wb') as f:
			f.write(self.current_captcha)
		logger.info("----------------Captcha saved---------------")
		self.current_count+=1
		if self.current_count >= MAX_CAPTCHAS_DOWNLOAD:
			return
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
			callback = self.login_form
			request = scrapy.Request(url=captcha_url, callback=callback, dont_filter=True, errback=self.errback_next)
			request.meta['old_response'] = response
			yield request