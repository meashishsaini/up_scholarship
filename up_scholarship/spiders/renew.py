import scrapy
from datetime import datetime
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings
from up_scholarship.spiders.base import BaseSpider
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class RenewSpider(BaseSpider):
	name = 'renew'
	no_students = 0
	required_keys = [FormKeys.reg_year(), FormKeys.skip(), FormKeys.std(), FormKeys.name(), FormKeys.reg_no(),
																		FormKeys.dob(), FormKeys.mobile_no()]

	def __init__(self, *args, **kwargs):
		""" Load student's file and init variables"""
		super().__init__(RenewSpider, *args, **kwargs)

	def start_requests(self):
		self.i_students = self.skip_to_next_valid()
		self.save_if_done(raise_exc=False)
		if self.no_students > 0 and self.no_students != self.i_students:
			student = self.students[self.i_students]
			url = self.url_provider.get_renew_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def fill_form(self, response):
		logger.info('In fill form. Last URL: %s', response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_renew_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True)
		else:
			student = self.students[self.i_students]
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta['old_response']
			form_data = {
				FormKeys.reg_no(form=True): student[FormKeys.reg_no()],
				FormKeys.dob(form=True): student[FormKeys.dob()],
				FormKeys.mobile_no(form=True): student.get(FormKeys.mobile_no(), ''),
				FormKeys.captcha_value(form=True): captcha_value,
				FormKeys.login(form=True): 'Submit',

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
		logger.info('In parse. Previous URL: %s', response.url)
		student = self.students[self.i_students]

		if response.url.find(TestStrings.renew_success) != -1:
			new_reg_no = response.xpath(
				'//*[@id="' + FormKeys.reg_no(form=True, reg=True) + '"]/text()').extract_first()
			vf_code = response.xpath('//*[@id="' + FormKeys.password(form=True, reg=True) + '"]/text()').extract_first()
			logger.info("----------------Application got renewed---------------")
			logger.info("New reg no.: %s vf_code: %s", new_reg_no, vf_code)
			print("----------------Application got renewed---------------")
			print("New reg no.:" + new_reg_no)
			src = utl.get_photo_by_uid_name(self.cd.data_dir, student, 'jpg ', student[FormKeys.reg_year()], FormKeys())
			student[FormKeys.old_reg_no()] = student[FormKeys.reg_no()]
			student[FormKeys.reg_no()] = new_reg_no
			student[FormKeys.password()] = vf_code
			student[FormKeys.status()] = "Success"
			student[FormKeys.std()] = str(int(student[FormKeys.std()]) + 1)
			#student[FormKeys.previous_school()] = student[FormKeys.institute()]
			student[FormKeys.reg_year()] = str(datetime.today().year)
			student = self.remove_old_values(student)
			dest = utl.get_photo_by_uid_name(
				self.cd.data_dir, student, 'jpg ', student[FormKeys.reg_year()], FormKeys())
			try:
				utl.copy_file(src, dest)
			except Exception as err:
				print(err)
			self.students[self.i_students] = student
			utl.save_file_with_name(student, response, self.spider_name, str(datetime.today().year))
			self.i_students += 1
			self.i_students = self.skip_to_next_valid()
			self.tried = 0
		else:
			self.process_errors(response, [TestStrings.renew_form, TestStrings.error, TestStrings.registration_new])
		self.save_if_done()
		student = self.students[self.i_students]
		url = self.url_provider.get_renew_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
		yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		logger.info("In Captcha. Last URL %s", response.url)
		if self.process_errors(response, [TestStrings.error]):
			student = self.students[self.i_students]
			url = self.url_provider.get_renew_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_url = self.url_provider.get_captcha_url()

			request = scrapy.Request(url=captcha_url, callback=self.fill_form, dont_filter=True, errback=self.errback_next)
			request.meta['old_response'] = response
			yield request

	def skip_to_next_valid(self) -> int:
		length = len(self.students)
		for x in range(self.i_students, length):
			student = self.students[x]
			# If these required keys are not available continue
			if not utl.check_if_keys_exist(student, self.required_keys):
				logger.info('skipping ' + student[FormKeys.name()])
				continue
			reg_year = int(student.get(FormKeys.reg_year(), '0')) if len(student.get(FormKeys.reg_year(), '')) > 0 else 0
			if reg_year != 0 and reg_year < datetime.today().year and student[FormKeys.skip()] == 'N':
				if student[FormKeys.std()] == '9' or student[FormKeys.std()] == '11':
					print('Renewing application of: ' + student[FormKeys.name()] + ' reg_no: ' + student[
						FormKeys.reg_no()] + ' of std: ' + student[FormKeys.std()])
					return x
				elif student[FormKeys.std()] == '10':
					print('Upgrading student: %s %s of std: %s reg_year: %s' % (
						student[FormKeys.name()], student[FormKeys.reg_no()], student[FormKeys.std()], student[FormKeys.reg_year()]))
					src = utl.get_photo_by_uid_name(
						self.cd.data_dir, student, 'jpg ', student[FormKeys.reg_year()], FormKeys())
					student[FormKeys.std()] = '11'
					student[FormKeys.reg_year()] = ''
					student[FormKeys.status()] = ''
					student[FormKeys.reg_no()] = ''
					student[FormKeys.old_reg_no()] = ''
					student[FormKeys.previous_school()] = ''
					student[FormKeys.password()] = ''
					student = self.remove_old_values(student)
					dest = utl.get_photo_by_uid_name(
						self.cd.data_dir, student, 'jpg ', str(datetime.today().year), FormKeys())
					utl.copy_file(src, dest)
					self.students[x] = student
				elif student[FormKeys.std()] == '12':
					student[FormKeys.skip()] = 'Y'
					self.students[x] = student
		return self.no_students

	def remove_old_values(self, student: dict) -> dict:
		# student[FormKeys.lastyear_std()] = ''
		# student[FormKeys.last_year_result()] = ''
		# student[FormKeys.lastyear_total_marks()] = ''
		# student[FormKeys.lastyear_obtain_marks()] = ''
		# student[FormKeys.admission_date()] = ''
		# student[FormKeys.tuition_fees()] = ''
		# student[FormKeys.lastyear_scholarship_amt()] = ''
		# student[FormKeys.fees_receipt_no()] = ''
		# student[FormKeys.total_fees_left()] = ''
		# student[FormKeys.total_fees_submitted()] = ''
		# student[FormKeys.total_fees()] = ''
		# student[FormKeys.fees_receipt_date()] = ''
		# student[FormKeys.board_reg_no()] = ''
		# student[FormKeys.institute()] = ''
		student[FormKeys.app_filled()] = 'N'
		student[FormKeys.photo_uploaded()] = 'N'
		student[FormKeys.submitted_for_check()] = 'N'
		student[FormKeys.final_submitted()] = 'N'
		student[FormKeys.final_printed()] = 'N'
		student[FormKeys.app_received()] = 'N'
		student[FormKeys.app_verified()] = 'N'
		student[FormKeys.app_forwarded()] = 'N'
		return student
