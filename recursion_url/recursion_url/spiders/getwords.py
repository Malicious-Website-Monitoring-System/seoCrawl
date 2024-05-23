import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from scrapy.selector import Selector
from collections import deque
import re

# 단어 분류를 위한 리스트
casino = ["도박", "카지노", "또또", "로또", "환불", "포인트"]
adult = ["19", "유흥", "오피", "정화", "한국", "야동", "BJ"]

class HostSpider(scrapy.Spider):
    name = "getwords"
    handle_httpstatus_list = [403, 404]  # HTTP 403, 404 상태 코드를 처리하도록 설정

    def __init__(self, *args, **kwargs):
        super(HostSpider, self).__init__(*args, **kwargs)
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.divide_file = open('divide.txt', 'w')
        self.hosts_queue = deque(open('hosts.txt', 'r').read().strip().split("\n"))  # 호스트 파일에서 불러오기

    def start_requests(self):
        yield scrapy.Request(url="http://example.com", callback=self.parse)

    def parse(self, response):
        while self.hosts_queue:
            current_host = self.hosts_queue.popleft()
            self.process_host(current_host)

    def process_host(self, current_host):
        self.log(f"Processing host: {current_host}")
        try:
            self.driver.get(current_host)
            html = self.driver.page_source
            selector = Selector(text=html)
            self.classify_and_write(current_host, selector)
        except Exception as e:
            self.log(f"Exception occurred while processing {current_host}: {e}")
            self.divide_file.write(f"{current_host}: 접속 불가\n")

    def classify_and_write(self, url, selector):
        text = ' '.join(selector.css('::text').extract())
        words = re.findall(r'\b\w+\b', text.lower())

        casino_count = sum(word in casino for word in words)
        adult_count = sum(word in adult for word in words)

        if casino_count >= 3 and adult_count >= 3:
            site_type = "링크 공유 사이트"
        elif casino_count >= 3:
            site_type = "카지노 사이트"
        elif adult_count >= 3:
            site_type = "성인 사이트"
        else:
            site_type = "정상 사이트"

        self.divide_file.write(f"{url}: {site_type}\n")
        self.log(f"{url}: {site_type}")

    def closed(self, reason):
        self.driver.quit()
        self.divide_file.close()