from scrapy.crawler import CrawlerProcess
import argparse

def parse():
	parser = argparse.ArgumentParser()
	spiders_list = ["register", "filldata", "uploadphoto", "submitcheck", "renew", "submitfinal", "receive", "verify", "forward", "aadhaarauth", "savecaptchas"]
	tools_list = ["scanphoto", "convert2pdf", "printfinal", "donestudent"]
	parser.add_argument('work', help="tell which spider needed to be run.", choices=spiders_list + tools_list)
	parser.add_argument("--filepath", "-f", help="path of input file", type=str)
	args = parser.parse_args()
	if args.work in spiders_list:
		process = CrawlerProcess({
			'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
		})
		if args.work == "register":
			from up_scholarship.spiders.register import RegisterSpider
			process.crawl(RegisterSpider)
		elif args.work == "filldata":
			from up_scholarship.spiders.filldata import FillDataSpider
			process.crawl(FillDataSpider)
		elif args.work == "uploadphoto":
			from up_scholarship.spiders.uploadphoto import UploadPhotoSpider
			process.crawl(UploadPhotoSpider)
		elif args.work == "submitcheck":
			from up_scholarship.spiders.submitcheck import SubmitDataspider
			process.crawl(SubmitDataspider)
		elif args.work == "renew":
			from up_scholarship.spiders.renew import RenewSpider
			process.crawl(RenewSpider)
		elif args.work == "submitfinal":
			from up_scholarship.spiders.finalsubmit import FinalSubmitDataSpider
			process.crawl(FinalSubmitDataSpider)
		elif args.work == "receive":
			from up_scholarship.spiders.receive import ReceiveAppSpider
			process.crawl(ReceiveAppSpider)
		elif args.work == "verify":
			from up_scholarship.spiders.verify import VerifyAppSpider
			process.crawl(VerifyAppSpider)
		elif args.work == "forward":
			from up_scholarship.spiders.forward import ForwardAppSpider
			process.crawl(ForwardAppSpider)
		elif args.work == "aadhaarauth":
			from up_scholarship.spiders.aadhaar_auth import AadhaarAuthSpider
			process.crawl(AadhaarAuthSpider)
		elif args.work == "savecaptchas":
			from up_scholarship.spiders.save_captchas import SaveCatpchasSpider
			process.crawl(SaveCatpchasSpider)
		process.start()
	elif args.work == "scanphoto":
		from up_scholarship.tools.photo_scan_helper import scan_photos
		scan_photos()
	elif args.work == "convert2pdf":
		from up_scholarship.tools.convert2pdf import convert2pdf
		convert2pdf()
	elif args.work == "printfinal":
		from up_scholarship.tools.printfinal import print_final
		print_final()
	elif args.work == "donestudent":
		from up_scholarship.tools.student_done_helper import is_student_done
		is_student_done(args.filepath)