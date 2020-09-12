from scrapy import Spider, Request
from pprint import pprint
class BankSpider(Spider):
	name = "bank"
	start_urls = ["file:///C:/Users/saini/Desktop/Bank of Baroda.html"]

	def parse(self, response):
		options = response.xpath('//*[@id="ContentPlaceHolder1_ddl_bankname"]/option')
		banks = {option.xpath("text()").extract_first(): option.xpath("@value").extract_first() for option in options}
		for name, value in banks.items():
			print(f'"{name.lower()}":	"{value}",')

if __name__ == "__main__":
	from scrapy.crawler import CrawlerProcess
	process = CrawlerProcess({
			'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
		})
	process.crawl(BankSpider)
	process.start()