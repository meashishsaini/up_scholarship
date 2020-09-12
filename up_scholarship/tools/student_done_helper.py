from up_scholarship.providers.student_file import StudentFile
from up_scholarship.providers.constants import CommonData, FormKeys
import os
import logging
from rich.table import Table
from rich.console import Console
logger = logging.getLogger(__name__)

def status_str(student, key):
	status = student[key]
	if key == FormKeys.reg_no():
		status = "Y" if student[key] else "N"
	return "[[green]✓[/green]]" if (status == 'Y') else "[[red]✕[/red]]"
def is_student_done(filepath: str):
	cd = CommonData()
	console = Console()
	students = StudentFile().read_file(filepath if filepath else cd.students_in_file, cd.file_in_type)
	while True:
		found = False
		os.system('cls')
		UID_no = input('Please enter UID number. ')
		if len(UID_no) == 12:
			for st in students:
				if UID_no == st[FormKeys.aadhaar_no()]:
					grid = Table.grid(expand=True, padding=(0,1,0,0))
					grid.add_column(style="bold blue")
					grid.add_column(style="yellow")
					grid.add_row("Name:", st[FormKeys.name()])
					grid.add_row("Std:", st[FormKeys.std()])
					grid.add_row("Reg Year:", st[FormKeys.reg_year()])
					grid.add_row("Institute:", st[FormKeys.institute()])
					grid.add_row("","")
					grid.add_row("Skipped:", status_str(st, FormKeys.skip()))
					grid.add_row("","")
					grid.add_row("Registered:", status_str(st, FormKeys.reg_no()))
					grid.add_row("Application Filled:", status_str(st, FormKeys.app_filled()))
					grid.add_row("Photo Uploaded:", status_str(st, FormKeys.photo_uploaded()))
					grid.add_row("Submitted for check:", status_str(st, FormKeys.submitted_for_check()))
					grid.add_row("Final Submitted:", status_str(st, FormKeys.final_submitted()))
					grid.add_row("Final Printed:", status_str(st, FormKeys.final_printed()))
					grid.add_row("","")
					grid.add_row("Application Received:", status_str(st, FormKeys.app_received()))
					grid.add_row("Application Verified:", status_str(st, FormKeys.app_verified()))
					grid.add_row("Application Forwarded:", status_str(st, FormKeys.app_forwarded()))
					grid.add_row("","")
					grid.add_row("Last status msg:", st[FormKeys.status()])
					grid.add_row("","")
					console.print(grid)
					input("Press enter to continue.")
					found = True
			if not found:
				print("UID not found.")
				input("Press enter to continue.")
		else:
			print("Bye bye")
			break
