from scrapy.crawler import CrawlerProcess
from up_scholarship.spiders.register import RegisterSpider
from up_scholarship.spiders.filldata import FillDataSpider
from up_scholarship.spiders.uploadphoto import UploadPhotoSpider
from up_scholarship.spiders.submitcheck import SubmitDataspider
from up_scholarship.spiders.receive import ReceiveAppSpider
from up_scholarship.spiders.renew import RenewSpider
from up_scholarship.spiders.finalsubmit import FinalSubmitDataSpider
from up_scholarship.spiders.verify import VerifyAppSpider
from up_scholarship.spiders.forward import ForwardAppSpider
from up_scholarship.tools.photo_scan_helper import scan_photos
from up_scholarship.tools.convert2pdf import convert2pdf
from up_scholarship.tools.printfinal import print_final
from up_scholarship.tools.student_done_helper import is_student_done
import os
import sys
import argparse
def parse():
	parser = argparse.ArgumentParser()
	spiders_list = ["register", "filldata", "uploadphoto", "submitcheck", "renew", "submitfinal", "receive", "verify", "forward"]
	tools_list = ["scanphoto", "convert2pdf", "printfinal", "donestudent"]
	parser.add_argument('work', help="tell which spider needed to be run.", choices=spiders_list + tools_list)
	parser.add_argument("--filepath", "-f", help="path of input file", type=str)
	args = parser.parse_args()
	if args.work in spiders_list:
		process = CrawlerProcess({
			'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
		})
		if args.work == "register":
			process.crawl(RegisterSpider)
		elif args.work == "filldata":
			process.crawl(FillDataSpider)
		elif args.work == "uploadphoto":
			process.crawl(UploadPhotoSpider)
		elif args.work == "submitcheck":
			process.crawl(SubmitDataspider)
		elif args.work == "renew":
			process.crawl(RenewSpider)
		elif args.work == "submitfinal":
			process.crawl(FinalSubmitDataSpider)
		elif args.work == "receive":
			process.crawl(ReceiveAppSpider)
		elif args.work == "verify":
			process.crawl(VerifyAppSpider)
		elif args.work == "forward":
			process.crawl(ForwardAppSpider)
		process.start()
	elif args.work == "scanphoto":
		scan_photos()
	elif args.work == "convert2pdf":
		convert2pdf()
	elif args.work == "printfinal":
		print_final()
	elif args.work == "donestudent":
		is_student_done(args.filepath)