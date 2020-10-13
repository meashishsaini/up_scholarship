from setuptools import setup

def readme():
	with open("README.rst") as f:
		return f.read()

install_requires = [
	"pywin32",
	"scrapy",
	"openpyxl",
	"imutils",
	"opencv-contrib-python",
	"tensorflow",
	"requests",
	"pdfkit",
	"Pillow",
	"pyperclip",
	"dlib",
	"pyinsane2",
	"rich",
	"pycryptodome",
	"D:\Data\Projects\python\scan_helper"
]

setup(name="up-scholarship",
	version="0.2",
	description="Scripts to fill scholarship forms",
	long_description=readme(),
	classifiers=[
	"Development Status :: 3 - Alpha",
	"License :: OSI Approved :: MIT License",
	"Programming Language :: Python :: 3.7",
	"Topic :: Utilities",
	],
	keywords="up scholarship",
	#url="http://github.com/meashishsaini/bsnl",
	author="Ashish Saini",
	author_email="sainiashish08@gmail.com",
	license="MIT",
	packages=["up_scholarship"],
	install_requires=install_requires,
	# test_suite="nose.collector",
	# tests_require=["nose", "nose-cover3"],
	entry_points={
	"console_scripts": ["up_scholarship=up_scholarship.main:parse"],
	},
	include_package_data=True,
	zip_safe=False)
