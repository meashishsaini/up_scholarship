from scrapy import Spider, Request
from pprint import pprint
class BranchSpider(Spider):
	name = "branch"
	start_urls = ["file:///C:/Users/saini/Desktop/Rampur Zila Sahakari Bank.html"]

	def parse(self, response):
		options = response.xpath('//*[@id="ContentPlaceHolder1_ddl_Branchname"]/option')
		branches = {option.xpath("text()").extract_first(): option.xpath("@value").extract_first() for option in options}
		for name, value in branches.items():
			print(f'"{name.lower()}":	"{value}",')

if __name__ == "__main__":
	from scrapy.crawler import CrawlerProcess
	process = CrawlerProcess({
			'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
		})
	process.crawl(BranchSpider)
	process.start()