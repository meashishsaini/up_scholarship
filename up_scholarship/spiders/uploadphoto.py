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
from up_scholarship.spiders.base import BaseSpider
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class UploadPhotoSpider(BaseSpider):
	name = 'uploadphoto'
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.reg_no(), FormKeys.dob(), FormKeys.name(), FormKeys.app_filled(),
		FormKeys.photo_uploaded(), FormKeys.father_name()]
	non_minority_keys = [
		FormKeys.subcaste(), FormKeys.caste_cert_issue_date(), FormKeys.caste_cert_name(), FormKeys.caste_cer_app_no(),
		FormKeys.caste_cert_no()]
	post_required_keys = [
		FormKeys.high_school_obtain_marks(), FormKeys.high_school_total_marks(), FormKeys.total_fees(),
		FormKeys.tuition_fees(), FormKeys.total_fees_submitted(), FormKeys.fees_receipt_no(),
		FormKeys.fees_receipt_date(), FormKeys.total_fees_left()]

	def __init__(self, *args, **kwargs):
		''' Load student's file and init variables'''
		super().__init__(UploadPhotoSpider, *args, **kwargs)

	def start_requests(self):
		self.i_students = self.skip_to_next_valid()
		self.save_if_done(raise_exc=False)
		if self.no_students > 0 and self.no_students != self.i_students:
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def login_form(self, response):
		logger.info('In login form. Last Url: %s', response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			self.save_if_done()
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			student = self.students[self.i_students]
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta['old_response']

			# Extract hf for password
			hf = response.xpath('//*[@id="' + FormKeys.hf(self.cd.current_form_set) + '"]/@value').extract_first()

			form_data = utl.get_login_form_data(student, hf, self.is_renewal, captcha_value, FormKeys(), self.cd.current_form_set)
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.accept_popup,
				errback=self.errback_next,
				dont_filter=True
			)
			yield request

	def accept_popup(self, response):
		''' If we get popup about accepting terms accept them and if not continue filling other things.
			Keyword arguments:
			response -- previous scrapy response.
		'''
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
			url = self.url_provider.get_photo_up_url(student.get(FormKeys.std(), ''), app_id, self.is_renewal)
			logger.info("URL: %s", url)
			yield scrapy.Request(url=url, callback=self.upload_photo, dont_filter=True, errback=self.errback_next)
		# Popup might not have been accepted, accept it
		else:
			logger.info('Accepting popup. Last URL: %s', response.url)
			request = scrapy.FormRequest.from_response(
				response,
				formdata={
					FormKeys.check_popup_agree(form=True): 'on',
					FormKeys.popup_button(form=True): 'Proceed >>>',
				},
				callback=self.accept_popup,
				errback=self.errback_next,
				dont_filter=True,
			)
			yield request

	def upload_photo(self, response):
		logger.info('In upload photo. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			headers = response.request.headers

			parsed = urlparse.urlparse(response.url)
			app_id = urlparse.parse_qs(parsed.query)['Appid'][0]
			student = self.students[self.i_students]
			url = self.url_provider.get_photo_up_url(student.get(FormKeys.std(), ''), app_id, self.is_renewal)

			viewstate = response.xpath('//*[@id="' + FormKeys.view_state() + '"]/@value').extract_first()
			viewstategenerater = response.xpath \
				('//*[@id="' + FormKeys.view_state_generator() + '"]/@value').extract_first()
			eventvalidation = response.xpath('//*[@id="' + FormKeys.event_validation() + '"]/@value').extract_first()

			filename = utl.get_photo_by_uid_name(self.cd.data_dir, student, 'jpg ', student[FormKeys.reg_year()], FormKeys())
			if utl.check_if_file_exists(filename):
				pre = utl.get_std_category(student[FormKeys.std()]) == StdCategory.pre

				fields = [(FormKeys.view_state(), viewstate),
						(FormKeys.view_state_generator(), viewstategenerater),
						(FormKeys.view_state_encrypted(), ''),
						(FormKeys.event_validation(), eventvalidation),
						(FormKeys.upload_photo(self.cd.current_form_set, form=True),
							'Upload Photo')]
				if not pre:
					fields.append((FormKeys.is_pic_upload(), "Y"))
					fields.append((FormKeys.is_handi_upload(), ""))
					fields.append((FormKeys.handi_type(), "0"))

				files = [(FormKeys.upload_photo_name(form=True), student[FormKeys.aadhaar_no()] + ".jpg", open(filename, 'rb'))]
				logger.info('Photo file %s', files)
				logger.info('Photo fields %s', fields)
				content_type, body = utl.MultipartFormDataEncoder().encode(fields, files)
				headers['Content-Type'] = content_type
				headers['Content-length'] = str(len(body))

				request_with_cookies = Request(url=url, method='POST', headers=headers, body=body, dont_filter=True)
				yield request_with_cookies
			else:
				student[FormKeys.status()] = 'Photo file not found'
				self.students[self.i_students] = student
				self.i_students += 1
				self.i_students = self.skip_to_next_valid()
				self.save_if_done()
				student = self.students[self.i_students]
				url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
				yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def parse(self, response):
		logger.info('Parse Got URL: %s', response.url)
		student = self.students[self.i_students]

		upload_status = ''
		scripts = response.xpath('//script/text()').extract()
		for script in scripts:
			if len(script) > 10 and script.lower().find(TestStrings.alert) != -1:
				upload_status = script[7:-1]
				break
		if upload_status.lower().find(TestStrings.photo_uploaded) != -1:
			student[FormKeys.photo_uploaded()] = 'Y'
			student[FormKeys.status()] = 'Success'
			self.students[self.i_students] = student
			logger.info("----------------Photo successfully uploaded---------------")
			print("----------------Photo successfully uploaded---------------")
			self.i_students += 1
			self.i_students = self.skip_to_next_valid()
			self.tried = 0
		else:
			self.process_errors(response, [TestStrings.photo_upload, TestStrings.error])
		self.save_if_done()
		student = self.students[self.i_students]
		url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		print("In Captcha: " + response.url)
		if self.process_errors(response, [TestStrings.error]):
			student = self.students[self.i_students]
			url = self.url_provider.get_login_reg_url(student[FormKeys.std()], self.is_renewal)
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_url = self.url_provider.get_captcha_url()
			if response.url.lower().find(TestStrings.login) != -1:
				request = scrapy.Request(url=captcha_url, callback=self.login_form, dont_filter=True,
										 errback=self.errback_next)
			else:
				request = scrapy.Request(url=captcha_url, callback=self.upload_photo, dont_filter=True,
										 errback=self.errback_next)
			request.meta['old_response'] = response
			yield request

	def skip_to_next_valid(self) -> int:
		'''	Check if data for required entries are available in the student's list and return index of it.
			Return valid student index or else no. of students.
			Returns: int
		'''
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
			# Set return index if student is not marked for skipping, registration year is current year and
			# application is not filled.
			if student[FormKeys.skip()] == 'N' and reg_year == datetime.today().year and student[
				FormKeys.app_filled()] == 'Y' and student[FormKeys.photo_uploaded()] == 'N':
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
		if (return_index != -1):
			student = self.students[return_index]
			logger.info('Uploading photo of: ' + student[FormKeys.name()] + ' of std: ' + student[FormKeys.std()])
			return return_index
		else:
			return self.no_students