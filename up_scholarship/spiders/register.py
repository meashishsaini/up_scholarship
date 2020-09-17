from datetime import datetime
import scrapy
import logging

from up_scholarship.providers.constants import FormKeys, TestStrings, StdCategory, FormSets
from up_scholarship.spiders.base import BaseSpider
from up_scholarship.tools.solve_captcha_using_model import get_captcha_string
from up_scholarship.providers import utilities as utl

logger = logging.getLogger(__name__)

class RegisterSpider(BaseSpider):
	name = 'register'
	common_required_keys = [
		FormKeys.skip(), FormKeys.std(), FormKeys.name(), FormKeys.dob(), FormKeys.district(), FormKeys.institute(),
		FormKeys.caste(), FormKeys.father_name(), FormKeys.mother_name(), FormKeys.gender(), FormKeys.board()]
	pre_required_keys = [FormKeys.eight_passing_year(), FormKeys.eight_school()]
	post_required_keys = [FormKeys.high_school_passing_year(), FormKeys.high_school_roll_no(), FormKeys.high_school_name_address()]

	def __init__(self, *args, **kwargs):
		''' Load student's file and init variables'''
		super().__init__(RegisterSpider, *args, **kwargs)

	def start_requests(self):
		""" Get registration page if we have some students"""
		self.i_students = self.skip_to_next_valid()
		self.save_if_done(raise_exc=False)
		if self.no_students > 0 and self.no_students != self.i_students:
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)

	def get_district(self, response):
		logger.info('In getting district. Last Url: %s', response.url)
		if self.process_errors(response, [TestStrings.error]):
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True)
		else:
			student = self.students[self.i_students]
			form_data = {
				FormKeys.event_target()			: FormKeys.district(form=True),
				FormKeys.district(form=True)	: self.district.get_code(student[FormKeys.district()])
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
		logger.info('In getting institute. Last Url: %s', response.url)
		if self.process_errors(response, [TestStrings.error]):
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True)
		else:
			student = self.students[self.i_students]
			form_data = {
				FormKeys.event_target()			: FormKeys.institute(form=True),
				FormKeys.district(form=True)	: self.district.get_code(student[FormKeys.district()]),
				FormKeys.institute(form=True)	: self.institute.get_code(student[FormKeys.institute()])
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
		logger.info('In get caste. Last Url: %s', response.url)
		if self.process_errors(response, [TestStrings.error]):
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True)
		else:
			student = self.students[self.i_students]
			form_data = {
				FormKeys.event_target()      : FormKeys.caste(form=True),
				FormKeys.district(form=True) : self.district.get_code(student[FormKeys.district()]),
				FormKeys.institute(form=True): self.institute.get_code(student[FormKeys.institute()]),
			}
			if student[FormKeys.is_minority()] == 'Y':
				form_data[FormKeys.caste(form=True)] = self.caste.get_code('min')
			else:
				form_data[FormKeys.caste(form=True)] = self.caste.get_code(student[FormKeys.caste()])
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
		logger.info('In reg form. Last Url: %s', response.url)
		if self.process_errors(response, [TestStrings.error], html=False):
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_institute, dont_filter=True)
		else:
			student = self.students[self.i_students]
			captcha_value = get_captcha_string(response.body)

			# Get old response after getting captcha
			response = response.meta['old_response']

			form_data, password = self.get_form_data(student, captcha_value)
			request = scrapy.FormRequest.from_response(
				response,
				formdata=form_data,
				callback=self.parse,
				errback=self.errback_next,
				dont_filter=True
			)
			request.meta['password'] = password
			yield request

	def parse(self, response):
		logger.info('In parse. Last URL: %s ', response.url)
		student = self.students[self.i_students]

		if response.url.find(TestStrings.registration_success) != -1:
			reg_no = response.xpath('//*[@id="' + FormKeys.reg_no(form=True, reg=True) + '"]/text()').extract_first()
			student[FormKeys.reg_no()] = reg_no
			student[FormKeys.password()] = response.meta['password']
			student[FormKeys.status()] = "Success"
			student[FormKeys.reg_year()] = str(datetime.today().year)
			self.students[self.i_students] = student
			logger.info("----------------Application got registered---------------")
			logger.info("Reg no.: %s password: %s", reg_no, response.meta['password'])
			utl.save_file_with_name(student, response, self.spider_name, str(datetime.today().year))
			self.i_students += 1
			self.i_students = self.skip_to_next_valid()
			self.tried = 0
		else:
			self.process_errors(response, [TestStrings.registration_form, TestStrings.error])
		self.save_if_done()
		student = self.students[self.i_students]
		url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
		yield scrapy.Request(url=url, callback=self.get_district, dont_filter=True, errback=self.errback_next)

	def get_captcha(self, response):
		print("In Captcha. Last URL: " + response.url)
		if self.process_errors(response, [TestStrings.error]):
			student = self.students[self.i_students]
			url = self.url_provider.get_reg_url(student[FormKeys.caste()], student[FormKeys.std()], student[FormKeys.is_minority()] == 'Y')
			yield scrapy.Request(url=url, callback=self.get_captcha, dont_filter=True, errback=self.errback_next)
		else:
			captcha_url = self.url_provider.get_captcha_url()
			request = scrapy.Request(url=captcha_url, callback=self.fill_reg, dont_filter=True,
									 errback=self.errback_next)
			request.meta['old_response'] = response
			yield request

	def skip_to_next_valid(self) -> int:
		length = len(self.students)
		return_index = -1
		for x in range(self.i_students, length):
			student = self.students[x]
			# If these required FormKeys are not available continue
			if not utl.check_if_keys_exist(student, self.common_required_keys):
				continue
			std_cat = utl.get_std_category(student[FormKeys.std()])
			if std_cat == StdCategory.pre and not utl.check_if_keys_exist(student, self.pre_required_keys):
				continue
			elif std_cat == StdCategory.post and not utl.check_if_keys_exist(student, self.post_required_keys):
				continue
			elif std_cat == StdCategory.unknown:
				continue
			reg_year = int(student.get(FormKeys.reg_year(), '')) if len(student.get(FormKeys.reg_year(), '')) > 0 else 0

			if student[FormKeys.skip()] == 'N' and reg_year == 0:
				return_index = x
				student[FormKeys.reg_no()] = ''
				student[FormKeys.old_reg_no()] = ''
				self.students[x] = student
				break

		if return_index != -1:
			student = self.students[return_index]
			print('Registering application of: ' + student[FormKeys.name()] + ' of std: ' + student[FormKeys.std()])
			return return_index
		else:
			return self.no_students

	def get_form_data(self, student: dict, captcha_value):
		father_husband_name = ''
		if student[FormKeys.father_name()] != '':
			father_husband_name = student[FormKeys.father_name()]
		else:
			father_husband_name = student[FormKeys.husband_name()]
		password = utl.get_random_password()
		hashed_password, _ = utl.get_login_form_password(password)
		form_data = {
			FormKeys.district(form=True)           : self.district.get_code(student[FormKeys.district()]),
			FormKeys.institute(form=True)          : self.institute.get_code(student[FormKeys.institute()]),
			FormKeys.religion(form=True)           : self.religion.get_code(student[FormKeys.religion()]),
			FormKeys.name(form=True)               : student[FormKeys.name()],
			FormKeys.father_name(form=True)        : father_husband_name,
			FormKeys.mother_name(form=True)        : student[FormKeys.mother_name()],
			FormKeys.dob(form=True, reg=True)      : student[FormKeys.dob()],
			FormKeys.gender(form=True)             : student[FormKeys.gender()],
			FormKeys.board(form=True)              : self.board.get_code(student[FormKeys.board()]),
			FormKeys.mobile_no(form=True, reg=True): student[FormKeys.mobile_no()],
			FormKeys.password(form=True)           : hashed_password,
			FormKeys.confirm_password(form=True)   : hashed_password,
			FormKeys.captcha_value(form=True)      : captcha_value,
			FormKeys.submit(form=True)             : 'Submit',
		}
		if student[FormKeys.is_minority()] == 'Y':
			form_data[FormKeys.caste(form=True)] = self.caste.get_code('min')
		else:
			form_data[FormKeys.caste(form=True)] = self.caste.get_code(student[FormKeys.caste()])
		if utl.get_std_category(student[FormKeys().std()]) == StdCategory.pre:
			form_data[FormKeys.eight_passing_year(form=True)] = student[FormKeys.eight_passing_year()]
			form_data[FormKeys.eight_school(form=True)] = student[FormKeys.eight_school()]

		else:
			form_data[FormKeys.high_school_passing_year(form=True)] = student[FormKeys.high_school_passing_year()]
			form_data[FormKeys.high_school_roll_no(form=True)] = student[FormKeys.high_school_roll_no()]
			form_data[FormKeys.high_school_name_address(form=True)] = student[FormKeys.high_school_name_address()]
		return form_data, password
