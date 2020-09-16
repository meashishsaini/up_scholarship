from enum import Enum, auto
from datetime import datetime
from dataclasses import dataclass

class StdCategory(Enum):
	unknown = auto()
	pre = auto()
	post = auto()


class WorkType(Enum):
	register = auto()
	fill_data = auto()
	photo = auto()
	submit_check = auto()
	final_submit = auto()
	renew = auto()
	receive = auto()
	verify = auto()
	forward = auto()

@dataclass
class TestStrings:
	error = 'error'
	registration_new = 'RegistrationNew'
	registration_success = 'RegistrationPrint'
	registration_form = 'RegistrationForm'
	renew_success = 'RegistrationPrint'
	app_new_filled = 'applicationAccept'
	app_renew_filled = 'applicationCorrect'
	photo_upload = 'uploadphoto'
	photo_uploaded = 'successfully'
	app_default = 'default'
	login = 'login'
	app_fill_form = 'Form'
	renew_form = 'Renew'
	alert = 'alert'
	invalid_captcha = 'Invalid Captcha.!!'
	matched = 'yes'
	final_print = 'finalprint'
	show_image = 'showimage'
	final_disclaimer = 'finaldisclaimer'
	institute_login_success = 'prematric/index'
	application_received = 'Application Recieved Successfully !'
	application_verified = 'Application Verified Successfully !'
	application_forwarded = '1  Records Forwarded Successfully !'


class StudentFileTypes(Enum):
	unknown = auto()
	json = auto()
	excel = auto()


class FormSets(Enum):
	unknown = auto()
	one = auto()
	two = auto()
	three = auto()
	four = auto()

@dataclass
class CommonData:
	max_tries = 5
	data_dir = 'up_scholarship/data/'
	current_year = str(datetime.now().year)
	students_in_file = data_dir + 'students/%s/Students.xlsx' % current_year
	students_old_file = data_dir + 'students/%s/Students_old.xlsx' % current_year
	students_out_file = data_dir + 'students/%s/Students.xlsx' % current_year
	students_err_file = data_dir + 'students/%s/Students_err.json' % current_year
	religion_file = data_dir + 'codes/religion.json'
	bank_file = data_dir + 'codes/bank.json'
	board_file = data_dir + 'codes/board.json'
	branch_file = data_dir + 'codes/branch.json'
	caste_file = data_dir + 'codes/caste.json'
	course_file = data_dir + 'codes/course.json'
	district_file = data_dir + 'codes/district.json'
	sub_caste_file = data_dir + 'codes/subcaste.json'
	institute_file = data_dir + 'codes/institute.json'
	file_in_type = StudentFileTypes.excel
	file_out_type = StudentFileTypes.excel
	file_err_type = StudentFileTypes.json
	students_root_key = 'students'
	current_form_set = FormSets.one

	def set_form_set(self, current_form_set: FormSets):
		self.current_form_set = current_form_set

class FormKeys:
	prefix = 'ctl00$ContentPlaceHolder1$'

	@classmethod
	def district(cls, form=False):
		if form:
			return cls.prefix + 'ddl_district'
		else:
			return 'district'

	@classmethod
	def institute(cls, form=False):
		if form:
			return cls.prefix + 'ddl_institute'
		else:
			return 'institute'

	@classmethod
	def caste(cls, form=False):
		if form:
			return cls.prefix + 'ddl_caste'
		else:
			return 'caste'

	@classmethod
	def religion(cls, form=False):
		if form:
			return cls.prefix + 'ddl_relegion'
		else:
			return 'religion'

	@classmethod
	def name(cls, form=False):
		if form:
			return cls.prefix + 'txt_studentname'
		else:
			return 'name'

	@classmethod
	def father_name(cls, form=False):
		if form:
			return cls.prefix + 'txt_father_husbandname'
		else:
			return 'father_name'

	@classmethod
	def father_aadhaar_no(cls, form=False):
		if form:
			return cls.prefix + 'txtAadhar_Father'
		else:
			return 'father_aadhaar_no'

	@classmethod
	def mother_name(cls, form=False):
		if form:
			return cls.prefix + 'txt_mothername'
		else:
			return 'mother_name'

	@classmethod
	def mother_aadhaar_no(cls, form=False):
		if form:
			return cls.prefix + 'txtAadhar_Mother'
		else:
			return 'mother_aadhaar_no'

	@classmethod
	def dob(cls, form=False, reg=False):
		if form:
			return cls.prefix + ('txt_dob' if reg else 'txtdob')
		else:
			return 'dob'

	@classmethod
	def gender(cls, form=False):
		if form:
			return cls.prefix + 'ddl_gender'
		else:
			return 'gender'

	@classmethod
	def high_school_passing_year(cls, form=False):
		if form:
			return cls.prefix + 'ddl_highschpassyear'
		else:
			return 'high_school_passing_year'

	@classmethod
	def board(cls, form=False):
		if form:
			return cls.prefix + 'ddl_board'
		else:
			return 'board'

	@classmethod
	def high_school_roll_no(cls, form=False):
		if form:
			return cls.prefix + 'txt_hghrollno'
		else:
			return 'high_school_roll_no'

	@classmethod
	def high_school_name_address(cls, form=False):
		if form:
			return cls.prefix + 'txt_schnameAdd_10class'
		else:
			return 'high_school_name_address'

	@classmethod
	def mobile_no(cls, form=False, reg=False):
		if form:
			return cls.prefix + ('txt_mobileno' if reg else 'txt_Mob')
		else:
			return 'mobile_no'

	@classmethod
	def phone_no(cls, form=False):
		if form:
			return cls.prefix + 'txt_phoneno'
		else:
			return 'phone_no'

	@classmethod
	def email_id(cls, form=False):
		if form:
			return cls.prefix + 'txt_emailid'
		else:
			return 'email_id'

	@classmethod
	def password(cls, form=False, reg=False):
		if form:
			return 'lbl_pass' if reg else (cls.prefix + 'txt_pwd')
		else:
			return 'password'

	@classmethod
	def confirm_password(cls, form=False):
		if form:
			return cls.prefix + 'txt_pwd_confirm'
		else:
			return 'confirm_password'

	@classmethod
	def submit(cls, form=False):
		if form:
			return cls.prefix + 'btn_submit'
		else:
			return 'submit'

	@classmethod
	def captcha_value(cls, form=False):
		if form:
			return cls.prefix + 'txtCaptcha'
		else:
			return 'captcha_value'

	@classmethod
	def eight_passing_year(cls, form=False):
		if form:
			return cls.prefix + 'ddl_highschpassyear'
		else:
			return 'eight_passing_year'

	@classmethod
	def login(cls, form=False):
		if form:
			return cls.prefix + 'btnLogin'
		else:
			return 'login'

	@classmethod
	def eight_school(cls, form=False):
		if form:
			return cls.prefix + 'schname8class'
		else:
			return 'eight_school'

	@classmethod
	def reg_no(cls, form=False, reg=False):
		if form:
			return 'txt_appid' if reg else (cls.prefix + 'txtappid')
		else:
			return 'regno'

	@classmethod
	def permanent_address_1(cls, form=False):
		if form:
			return cls.prefix + 'txt_permanentaddress'
		else:
			return 'permanent_address_1'

	@classmethod
	def permanent_address_2(cls, form=False):
		if form:
			return cls.prefix + 'txt_permanentaddress1'
		else:
			return 'permanent_address_2'

	@classmethod
	def mailing_address_1(cls, form=False):
		if form:
			return cls.prefix + 'txt_mailingaddress'
		else:
			return 'mailing_address_1'

	@classmethod
	def mailing_address_2(cls, form=False):
		if form:
			return cls.prefix + 'txt_mailingaddress1'
		else:
			return 'mailing_address_2'

	@classmethod
	def lastyear_total_marks(cls, form=False):
		if form:
			return cls.prefix + 'total_marks'
		else:
			return 'lastyear_total_marks'

	@classmethod
	def lastyear_obtain_marks(cls, form=False):
		if form:
			return cls.prefix + 'obtain_marks'
		else:
			return 'lastyear_obtain_marks'

	@classmethod
	def subcaste(cls, form=False):
		if form:
			return cls.prefix + 'ddl_subcaste'
		else:
			return 'subcaste'

	@classmethod
	def caste_cert_issue_date(cls, form=False, pre=True):
		if form:
			return cls.prefix + ('txt_jaticrt_issuedate' if pre else 'txt_castecrt_issuedate')
		else:
			return 'caste_cert_issue_date'

	@classmethod
	def caste_cert_name(cls, form=False):
		if form:
			return cls.prefix + 'txt_std_jatinm'
		else:
			return 'caste_cert_name'

	@classmethod
	def caste_cer_app_no(cls, form=False, pre=True):
		if form:
			return cls.prefix + ('txt_niw_crtificateno' if pre else 'txt_casteserailno')
		else:
			return 'caste_cer_app_no'

	@classmethod
	def caste_cert_no(cls, form=False, pre=True):
		if form:
			return cls.prefix + ('txt_cst_crtificateno' if pre else 'txt_caste_crtificateno')
		else:
			return 'caste_cert_no'

	@classmethod
	def income_cert_issue_date(cls, form=False):
		if form:
			return cls.prefix + 'txt_incomecrt_issuedate'
		else:
			return 'income_cert_issue_date'

	@classmethod
	def income_cert_app_no(cls, form=False, pre=True):
		if form:
			return cls.prefix + ('txt_std_ninm' if pre else 'txt_incomeserailno')
		else:
			return 'income_cert_app_no'

	@classmethod
	def income_cert_no(cls, form=False):
		if form:
			return cls.prefix + 'txt_income_crtificateno'
		else:
			return 'income_cert_no'

	@classmethod
	def income_cert_name(cls, form=False):
		if form:
			return cls.prefix + 'txt_std_icmenm'
		else:
			return 'income_cert_name'

	@classmethod
	def annual_income(cls, form=False):
		if form:
			return cls.prefix + 'txt_totalincome'
		else:
			return 'annual_income'

	@classmethod
	def bank_account_no(cls, form=False):
		if form:
			return cls.prefix + 'txt_std_accno'
		else:
			return 'bank_account_no'
	@classmethod
	def bank_account_no_re(cls, form=False):
		if form:
			return cls.prefix + 'txt_std_accno_Re'
		else:
			return 'bank_account_no'

	@classmethod
	def bank_name(cls, form=False):
		if form:
			return cls.prefix + 'ddl_bankname'
		else:
			return 'bank_name'

	@classmethod
	def branch_name(cls, form=False):
		if form:
			return cls.prefix + 'ddl_Branchname'
		else:
			return 'branch_name'

	@classmethod
	def branch_dist_name(cls, form=False):
		if form:
			return cls.prefix + 'ddldistbnk'
		else:
			return 'branch_dist_name'

	@classmethod
	def bank_account_holder_name(cls, form=False):
		if form:
			return cls.prefix + 'txt_std_actnm'
		else:
			return 'bank_account_holder_name'

	@classmethod
	def aadhaar_no(cls, form=False, pre=True):
		if form:
			return cls.prefix + ('adharno' if pre else 'txt_Uid')
		else:
			return 'aadhaar_no'

	@classmethod
	def std(cls, form=False):
		if form:
			return cls.prefix + 'ddl_CourseName'
		else:
			return 'std'

	@classmethod
	def admission_date(cls, form=False, pre=True):
		if form:
			return cls.prefix + ('txt_fstyr_addmissiondt' if pre else 'txt_currentsessiondate')
		else:
			return 'admission_date'

	@classmethod
	def board_reg_no(cls, form=False):
		if form:
			return cls.prefix + 'txt_UniBrdRegno'
		else:
			return 'board_regno'

	@classmethod
	def tc_no(cls, form=False):
		if form:
			return cls.prefix + 'tcno'
		else:
			return 'tc_no'

	@classmethod
	def tc_date(cls, form=False):
		if form:
			return cls.prefix + 'tcdt'
		else:
			return 'tc_date'

	@classmethod
	def previous_school(cls, form=False, pre=True):
		if form:
			return cls.prefix + ('schlnm' if pre else 'txtLastYearSchool')
		else:
			return 'previous_school'

	@classmethod
	def check_agree(cls, form=False):
		if form:
			return cls.prefix + 'chkIAgry'
		else:
			return 'check_agree'

	@classmethod
	def check_popup_agree(cls, form=False):
		if form:
			return 'chk'
		else:
			return 'check_popup_agree'

	@classmethod
	def popup_button(cls, form=False):
		if form:
			return 'btnsub'
		else:
			return 'popup_button'

	@classmethod
	def high_school_obtain_marks(cls, form=False):
		if form:
			return cls.prefix + 'txtBordObtainMarks'
		else:
			return 'high_school_obtain_marks'

	@classmethod
	def high_school_total_marks(cls, form=False):
		if form:
			return cls.prefix + 'txtBordTotalMarks'
		else:
			return 'high_school_total_marks'

	@classmethod
	def total_fees(cls, form=False):
		if form:
			return cls.prefix + 'txt_refundAmt'
		else:
			return 'total_fees'

	@classmethod
	def tuition_fees(cls, form=False):
		if form:
			return cls.prefix + 'txtTutionFees'
		else:
			return 'tuition_fees'

	@classmethod
	def total_fees_submitted(cls, form=False):
		if form:
			return cls.prefix + 'txt_feeamount'
		else:
			return 'total_fees_submitted'

	@classmethod
	def fees_receipt_no(cls, form=False):
		if form:
			return cls.prefix + 'txt_receiptno'
		else:
			return 'fees_reciept_no'

	@classmethod
	def fees_receipt_date(cls, form=False):
		if form:
			return cls.prefix + 'txt_receiptdate'
		else:
			return 'fees_reciept_date'

	@classmethod
	def total_fees_left(cls, form=False):
		if form:
			return cls.prefix + 'txtRemainingAmount'
		else:
			return 'total_fees_left'

	@classmethod
	def disability(cls, form=False):
		if form:
			return cls.prefix + 'ddl_Handitype'
		else:
			return 'disability'

	@classmethod
	def lastyear_scholarship_amt(cls, form=False):
		if form:
			return cls.prefix + 'txt_lastyrscholarshipAmt'
		else:
			return 'lastyear_scholarship_amt'

	@classmethod
	def lastyear_std(cls, form=False):
		if form:
			return cls.prefix + 'txt_lastyrClass'
		else:
			return 'lastyear_std'

	@classmethod
	def lastyear_percentage(cls, form=False):
		if form:
			return cls.prefix + 'txtlastyearPercentage'
		else:
			return 'lastyear_percentage'

	@classmethod
	def login_type(cls, form=False):
		if form:
			return cls.prefix + 'rbtnLoginType'
		else:
			return 'login_type'

	@classmethod
	def login_reg_no(cls, form=False):
		if form:
			return cls.prefix + 'txtLogin'
		else:
			return 'regno'

	@classmethod
	def last_year_result(cls, form=False):
		if form:
			return cls.prefix + 'ddl_lastyrResult'
		else:
			return 'last_year_result'

	@classmethod
	def resident_type(cls, form=False):
		if form:
			return cls.prefix + 'rb_regidancestdnt'
		else:
			return 'resident_type'

	@classmethod
	def address_same(cls, form=False):
		if form:
			return cls.prefix + 'txt_chkaddress'
		else:
			return 'address_same'

	@classmethod
	def husband_name(cls, form=False):
		if form:
			return cls.prefix + 'txt_father_husbandname'
		else:
			return 'husband_name'

	@classmethod
	def school_type(cls, form=False):
		if form:
			return cls.prefix + 'sch_type'
		else:
			return 'school_type'

	@classmethod
	def school_name(cls, form=False):
		if form:
			return cls.prefix + 'ddl_schname'
		else:
			return 'school_name'

	@classmethod
	def text_password(cls, form=False):
		if form:
			return cls.prefix + 'txtPassword'
		else:
			return 'password'

	@classmethod
	def institute_login_button(cls, form=False):
		if form:
			return cls.prefix + 'btn_captcha'
		else:
			return 'Log+In'

	@classmethod
	def hd_pass_text(cls, form=False):
		if form:
			return cls.prefix + 'HDPASSTEXT'
		else:
			return 'ContentPlaceHolder1_HDPASSTEXT'

	@classmethod
	def application_type(cls, form=False):
		if form:
			return cls.prefix + 'apptype'
		else:
			return 'application_type'

	@classmethod
	def registration_number_search(cls, form=False):
		if form:
			return cls.prefix + 'txt_search'
		else:
			return 'registration_number_search'

	@classmethod
	def search_button(cls, form=False):
		if form:
			return cls.prefix + 'search'
		else:
			return 'Search'

	@classmethod
	def skip(cls):
		return 'skip'

	@classmethod
	def event_target(cls):
		return '__EVENTTARGET'

	@classmethod
	def view_state(cls):
		return '__VIEWSTATE'

	@classmethod
	def view_state_generator(cls):
		return '__VIEWSTATEGENERATOR'

	@classmethod
	def view_state_encrypted(cls):
		return '__VIEWSTATEENCRYPTED'

	@classmethod
	def event_validation(cls):
		return '__EVENTVALIDATION'

	@classmethod
	def status(cls):
		return 'status'

	@classmethod
	def reg_year(cls):
		return 'reg_year'

	@classmethod
	def old_reg_no(cls):
		return 'old_regno'

	@classmethod
	def error_lbl(cls, current_form_set):
		r = 'ContentPlaceHolder1_ErrorLbl'
		if current_form_set == FormSets.one:
			r = 'ctl00_' + r
		elif current_form_set == FormSets.four:
			r = 'ErrorLbl'
		return r

	@classmethod
	def first_app_id(cls):
		return 'ContentPlaceHolder1_chkgrid_hidApp_Id_0'

	@classmethod
	def first_forward_app_id(cls):
		return 'ContentPlaceHolder1_chkgrid_HyperLink1_0'

	@classmethod
	def application_receive_button(cls, form=False):
		if form:
			return cls.prefix + 'chkgrid$ctl02$lnkbtnRecieve'
		else:
			return 'Recieve'

	@classmethod
	def application_receive_agree(cls, form=False):
		if form:
			return cls.prefix + 'chkgrid$ctl02$chkIs'
		else:
			return 'on'
	@classmethod
	def application_forward_agree(cls, form=False):
		if form:
			return cls.prefix + 'chkgrid$ctl02$chkSelect'
		else:
			return 'on'

	@classmethod
	def application_forward_button(cls, form=False):
		if form:
			return cls.prefix + 'Button1'
		else:
			return 'Forward+Selected+Applications'

	@classmethod
	def application_verify_status(cls, form=False):
		if form:
			return cls.prefix + 'chkgrid$ctl02$ddl_VRstatus'
		else:
			return 'V'

	@classmethod
	def application_verify_link_button(cls):
		return cls.prefix + 'chkgrid$ctl02$LinkButton1'

	@classmethod
	def app_filled(cls):
		return 'app_filled'

	@classmethod
	def photo_uploaded(cls):
		return 'photo_uploaded'

	@classmethod
	def submitted_for_check(cls):
		return 'submitted_for_check'

	@classmethod
	def final_submitted(cls):
		return 'final_submitted'

	@classmethod
	def final_printed(cls):
		return 'final_printed'

	@classmethod
	def final_printed(cls):
		return 'final_printed'

	@classmethod
	def is_minority(cls):
		return 'is_minority'

	@classmethod
	def app_received(cls):
		return 'app_received'

	@classmethod
	def app_verified(cls):
		return 'app_verified'

	@classmethod
	def app_forwarded(cls):
		return 'app_forwarded'
	
	@classmethod
	def is_pic_upload(cls):
		return cls.prefix + 'IsPicUpload'

	@classmethod
	def is_handi_upload(cls):
		return cls.prefix + 'IsHandiUpload'

	@classmethod
	def handi_type(cls):
		return cls.prefix + 'HandiType'

	@classmethod
	def hf(cls, current_form_set, form=False):
		if form:
			return cls.prefix + 'hf'
		else:
			r = 'ContentPlaceHolder1_hf'
			if current_form_set == FormSets.one:
				r = 'ctl00_' + r
			elif current_form_set == FormSets.four:
				r = 'hf'
			return r

	@classmethod
	def renewal_button(cls, form=False):
		if form:
			return cls.prefix + 'rbtnFR'
		else:
			return 'renewal_button'

	@classmethod
	def upload_photo(cls, current_form_set, form=False, pre=True, renewal=False):
		if form:
			return cls.prefix + 'upload_photo'
		else:
			r = 'ContentPlaceHolder1_upload'
			if current_form_set == FormSets.one:
				r = 'ctl00_' + r
			elif current_form_set == FormSets.four:
				r = 'upload'
			return r

	@classmethod
	def upload_photo_name(cls, form=False):
		if form:
			return cls.prefix + 'FileUpload1'
		else:
			return 'upload_photo_name'

	@classmethod
	def view_photo(cls, current_form_set):
		r = 'ContentPlaceHolder1_View_Photo'
		if current_form_set == FormSets.one:
			r = 'ctl00_' + r
		elif current_form_set == FormSets.four:
			r = 'View_Photo'
		return r

	@classmethod
	def temp_submit_lock(cls, current_form_set, form=False):
		if form:
			return cls.prefix + 'Href_temp_lock'
		else:
			r = 'ContentPlaceHolder1_Href_temp_lock'
			if current_form_set == FormSets.one:
				r = 'ctl00_' + r
			elif current_form_set == FormSets.four:
				r = 'Href_temp_lock'
			return r

	@classmethod
	def income_cert_no_status(cls, current_form_set):
		r = 'ContentPlaceHolder1_Lbl_inc'
		if current_form_set == FormSets.one:
			r = 'ctl00_' + r
		elif current_form_set == FormSets.four:
			r = 'Lbl_inc'
		return r

	@classmethod
	def caste_cert_no_status(cls, current_form_set):
		r = 'ContentPlaceHolder1_Lbl_caste'
		if current_form_set == FormSets.one:
			r = 'ctl00_' + r
		elif current_form_set == FormSets.four:
			r = 'Lbl_caste'
		return r

	@classmethod
	def annual_income_status(cls, current_form_set):
		r = 'ContentPlaceHolder1_Lbl_inc1'
		if current_form_set == FormSets.one:
			r = 'ctl00_' + r
		elif current_form_set == FormSets.four:
			r = 'Lbl_inc1'
		return r

	@classmethod
	def final_form_status(cls, current_form_set):
		r = 'ContentPlaceHolder1_lbl_msg'
		if current_form_set == FormSets.one:
			r = 'ctl00_' + r
		elif current_form_set == FormSets.four:
			r = 'lbl_msg'
		return r

	@classmethod
	def high_school_status(cls, current_form_set):
		r = 'ContentPlaceHolder1_lbl_10thdetails'
		if current_form_set == FormSets.one:
			r = 'ctl00_' + r
		elif current_form_set == FormSets.four:
			r = 'lbl_10thdetails'
		return r
