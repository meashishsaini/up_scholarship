from up_scholarship.providers import utilities as utl
from up_scholarship.providers.constants import FormSets, StdCategory, CommonData
from up_scholarship.providers.codes import CodeFileReader
import random

class UrlProviders:
	def __init__(self, cd: CommonData):
		self.cd = cd
		self.caste = CodeFileReader(self.cd.caste_file)

	def get_base_url(self) -> str:
		if self.cd.current_form_set == FormSets.one:
			return 'https://scholarship.up.gov.in/'
		elif self.cd.current_form_set == FormSets.two:
			return 'http://164.100.181.104/'
		elif self.cd.current_form_set == FormSets.three:
			return 'http://164.100.181.105/scholarship/'
		else:
			# return 'http://pfms.upsdc.gov.in/sch1920/'
			return "https://scholarship.up.gov.in/"

	def get_captcha_url(self) -> str:
		return self.get_base_url() + 'captcha.ashx?id=' + repr(random.random())

	def _make_reg_url(
			self,
			is_minority,
			caste: str,
			std: str,
			pre_reg_url: str, post_reg_url: str,
			minority_str: dict, obc_str: dict,
			other_str: dict) -> str:
		base_url = self.get_base_url()
		caste = caste.lower()
		caste_code = self.caste.get_code(caste)

		if utl.get_std_category(std) == StdCategory.pre:
			key = 'pre'
			reg_url = base_url + pre_reg_url
		else:
			key = 'post'
			reg_url = base_url + post_reg_url

		if is_minority:
			return reg_url + minority_str[key]
		elif caste_code == self.caste.get_code('obc'):
			return reg_url + obc_str[key]
		else:
			return reg_url + other_str[key]

	def get_reg_url(self, caste: str, std: str, is_minority=False) -> str:
		pre_reg_url = 'RegistrationFormPrematric.aspx?C='
		post_reg_url = 'RegistrationFormIntermediate.aspx?C='
		minority_str = {'pre':'NA==', 'post':'NA=='}
		obc_str = {'pre':'MQ==', 'post':'MQ=='}
		other_str = {'pre':'Mg==', 'post':'Mg=='}
		return self._make_reg_url(is_minority, caste, std, pre_reg_url, post_reg_url, minority_str, obc_str, other_str)

	def get_renew_url(self, caste: str, std: str, is_minority=False) -> str:
		pre_renew_url = "RenewRegistrationPre.aspx?C="
		post_renew_url = "RenewRegistration.aspx?C="
		minority_str = {'pre':'NF9QcmVfUHJl', 'post':'NF9Qb3N0X0ludGVy'}
		obc_str = {'pre':'MV9QcmVfUHJl', 'post':'MV9Qb3N0X0ludGVy'}
		other_str = {'pre':'Ml9QcmVfUHJl', 'post':'Ml9Qb3N0X0ludGVy'}
		return self._make_reg_url(is_minority, caste, std, pre_renew_url, post_renew_url, minority_str, obc_str, other_str)

	def _make_other_url(
			self,
			is_renewal: bool,
			std: str,
			pre_url: str, pre_renew_url: str,
			post_url: str, post_renew_url: str,
			app_id='') -> str:
		return_url = self.get_base_url()
		if utl.get_std_category(std) == StdCategory.pre:
			if is_renewal:
				return_url = return_url + pre_renew_url
			else:
				return_url = return_url + pre_url
		else:
			if is_renewal:
				return_url = return_url + post_renew_url
			else:
				return_url = return_url + post_url
		if len(app_id) > 0:
			return_url = return_url + '?Appid=' + app_id
		return return_url

	def get_login_reg_url(self, std: str, is_renewal: bool) -> str:
		pre_login_url = 'LoginStudentPreFresh.aspx'
		pre_renew_login_url = 'LoginStudentPreRenew.aspx'
		post_login_url = 'LoginStudentPostInter.aspx'
		post_renew_login_url = 'LoginStudentPostRenewInter.aspx'

		return self._make_other_url(is_renewal, std, pre_login_url, pre_renew_login_url, post_login_url,
									post_renew_login_url)

	def get_fill_reg_url(self, std: str, app_id: str, is_renewal: bool) -> str:
		pre_fill_reg_url = 'PrematricStudents1920/ApplicationFormPrematric.aspx'
		post_fill_reg_url = 'PostMatric1920/ApplicationFormIntermediate.aspx'

		pre_fill_renewal_reg_url = 'PrematricStudents1920_Renewal/renewApplicationFormUpdatePrematric.aspx'
		post_fill_renewal_reg_url = 'PostMatric1920_Renewal/RenewFormUpdation_Inter.aspx'

		return self._make_other_url(
			is_renewal,
			std,
			pre_fill_reg_url,
			pre_fill_renewal_reg_url,
			post_fill_reg_url,
			post_fill_renewal_reg_url,
			app_id)

	def get_temp_print_url(self, std: str, app_id: str, is_renewal: bool) -> str:
		pre_fill_reg_url = 'PrematricStudents1920/TempPrintPrematric.aspx'
		post_fill_reg_url = 'PostMatric1920/TempPrintIntermediate.aspx'

		pre_fill_renewal_reg_url = 'PrematricStudents1920_Renewal/renewTempPrintPrematric.aspx'
		post_fill_renewal_reg_url = 'PostMatric1920_Renewal/renewTempPrint_Inter.aspx'

		return self._make_other_url(
			is_renewal,
			std,
			pre_fill_reg_url, pre_fill_renewal_reg_url,
			post_fill_reg_url, post_fill_renewal_reg_url, app_id)

	def get_img_print_url(self, std: str, app_id: str, is_renewal: bool) -> str:
		pre_fill_reg_url = 'PrematricStudents1920/ShowImagePrematric.aspx'
		post_fill_reg_url = 'PostMatric1920/ShowImage_1112.aspx'

		pre_fill_renewal_reg_url = 'PrematricStudents1920_Renewal/ShowImagePrematric_renew.aspx'
		post_fill_renewal_reg_url = 'PostMatric1920_Renewal/ShowImage_1112.aspx'

		return_url = self._make_other_url(
			is_renewal,
			std,
			pre_fill_reg_url, pre_fill_renewal_reg_url,
			post_fill_reg_url, post_fill_renewal_reg_url)
		return return_url + '?App_Id=' + app_id

	def get_final_disclaimer_url(self, std: str, app_id: str, is_renewal: bool) -> str:
		pre_fill_reg_url = 'PrematricStudents1920/FinalDisclaimer.aspx'
		post_fill_reg_url = 'PostMatric1920/FinalDisclaimer.aspx'

		pre_fill_renewal_reg_url = 'PrematricStudents1920_Renewal/FinalDisclaimer.aspx'
		post_fill_renewal_reg_url = 'PostMatric1920_Renewal/FinalDisclaimer.aspx'

		return self._make_other_url(
			is_renewal,
			std,
			pre_fill_reg_url, pre_fill_renewal_reg_url,
			post_fill_reg_url, post_fill_renewal_reg_url,
			app_id)

	def get_final_print_url(self, std: str, app_id: str, is_renewal: bool) -> str:
		pre_fill_reg_url = 'PrematricStudents1920/FinalPrintPrematric.aspx'
		post_fill_reg_url = 'PostMatric1920/FinalPrintIntermediate.aspx'

		pre_fill_renewal_reg_url = 'PrematricStudents1920_Renewal/renewFinalPrintPrematric.aspx'
		post_fill_renewal_reg_url = 'PostMatric1920_Renewal/RenewFinalPrint_Inter.aspx'

		return self._make_other_url(
			is_renewal,
			std,
			pre_fill_reg_url, pre_fill_renewal_reg_url,
			post_fill_reg_url, post_fill_renewal_reg_url,
			app_id)

	def get_photo_up_url(self, std: str, app_id: str, is_renewal: bool) -> str:
		pre_fill_reg_url = 'PrematricStudents1920/UploadPhotoPrematric.aspx'
		post_fill_reg_url = 'PostMatric1920/UploadPhotoIntermediate.aspx'

		pre_fill_renewal_reg_url = 'PrematricStudents1920_Renewal/renewUploadPhotoPrematric.aspx'
		post_fill_renewal_reg_url = 'PostMatric1920_Renewal/renewUploadPhotoIntermediate.aspx'

		return self._make_other_url(
			is_renewal,
			std,
			pre_fill_reg_url, pre_fill_renewal_reg_url,
			post_fill_reg_url, post_fill_renewal_reg_url,
			app_id)

	def get_institute_login_url(self, std: str):
		pre_login_url = 'PreMatricLogin.aspx'
		post_login_url = 'Inst_login.aspx'
		return self._make_other_url(False, std, pre_login_url, pre_login_url, post_login_url, post_login_url)

	def get_institute_receive_url(self, std: str):
		pre_url = 'prematric/recieve_app.aspx'
		post_url = 'postmatric/recieve_app.aspx'
		return self._make_other_url(False, std, pre_url, pre_url, post_url, post_url)

	def get_institute_verify_url(self, std: str):
		pre_url = 'prematric/Verify_app.aspx'
		post_url = 'prematric/Verify_app.aspx'
		return self._make_other_url(False, std, pre_url, pre_url, post_url, post_url)

	def get_institute_forward_url(self, std: str):
		pre_url = 'prematric/Fwd_app.aspx'
		post_url = 'prematric/Fwd_app.aspx'
		return self._make_other_url(False, std, pre_url, pre_url, post_url, post_url)