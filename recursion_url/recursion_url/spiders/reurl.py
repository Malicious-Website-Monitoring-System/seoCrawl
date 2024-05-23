import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from scrapy.selector import Selector
from collections import deque, defaultdict
from urllib.parse import urlparse, urljoin, unquote
import re

# 단어 분류를 위한 리스트
casino = ["도박", "카지노", "또또", "로또", "환불", "포인트"]
adult = ["19", "유흥", "오피", "정화", "한국", "야동", "BJ"]

start_url = "https://zzang4.com/"
parsed_start_url = urlparse(start_url)
start_host = parsed_start_url.netloc
count_url = {start_host: 1}
queue = deque([(start_url, 0)])  # (url, depth)
visited_urls = set([start_url])  # 중복 확인을 위해 방문한 URL을 저장할 집합
visited_hosts = set([start_host])  # 중복 확인을 위해 방문한 호스트를 저장할 집합

class ReurlSpider(scrapy.Spider):
    name = "reurl77"
    start_urls = [start_url]
    handle_httpstatus_list = [403]  # HTTP 403 상태 코드를 처리하도록 설정

    def __init__(self, *args, **kwargs):
        super(ReurlSpider, self).__init__(*args, **kwargs)
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.file = open('urls.txt', 'w')
        self.hosts_file = open('hosts.txt', 'w')
        self.divide_file = open('divide.txt', 'w')
        self.depth_limit = 5  # 기본값으로 초기화

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(ReurlSpider, cls).from_crawler(crawler, *args, **kwargs)
        spider.depth_limit = crawler.settings.getint('DEPTH_LIMIT', 5)  # 설정에서 깊이 제한 읽기
        return spider

    def parse(self, response):
        if response.status == 403:
            self.log(f"Access denied to {response.url}")
            return

        current_url, current_depth = queue.popleft()

        if current_depth > self.depth_limit:
            return

        self.driver.get(current_url)
        html = self.driver.page_source
        response = Selector(text=html)

        # URL 추출
        get_urls = response.css('a::attr(href)').extract()
        get_onclick_urls = self.extract_onclick_urls()
        all_urls = get_urls + get_onclick_urls

        for url in all_urls:
            if url.startswith('/'):
                url = urljoin(current_url, url)
            elif not url.startswith('http'):
                continue

            if url not in visited_urls:
                visited_urls.add(url)
                host = self.extract_host(url)
                count_url[host] = count_url.get(host, 0) + 1
                self.file.write(url + '\n')
                if host not in visited_hosts:
                    visited_hosts.add(host)
                    self.hosts_file.write("https://" + host + '\n')
                queue.append((url, current_depth + 1))

        print(count_url)

        if queue:
            next_url, next_depth = queue[0]
            yield scrapy.Request(next_url, callback=self.parse)
        else:
            self.process_hosts()

    def extract_onclick_urls(self):
        onclick_elements = self.driver.find_elements("xpath", "//*[@onclick]")
        urls = []
        for element in onclick_elements:
            onclick_attr = element.get_attribute('onclick')
            if "window.open" in onclick_attr:
                start = onclick_attr.find("('") + 2
                end = onclick_attr.find("')", start)
                url = onclick_attr[start:end]
                urls.append(unquote(url))  # URL 디코딩
        return urls

    def extract_host(self, url):
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        return host

    def normalize_url(self, url):
        parsed_url = urlparse(url)
        scheme = parsed_url.scheme
        netloc = parsed_url.netloc
        path = parsed_url.path
        if scheme == 'http':
            normalized_url = f"https://{netloc}{path}"
        else:
            normalized_url = f"{scheme}://{netloc}{path}"
        return normalized_url

    def process_hosts(self):
        self.driver.quit()
        self.file.close()
        self.hosts_file.close()

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.driver.options)
        self.host_queue = deque([line.strip() for line in open('hosts.txt', 'r').readlines()])

        while self.host_queue:
            current_host = self.host_queue.popleft()
            yield scrapy.Request(current_host, self.parse_host)

    def parse_host(self, response):
        if response.status == 403:
            self.log(f"Access denied to {response.url}")
            return

        current_url = response.url
        self.driver.get(current_url)
        html = self.driver.page_source
        response = Selector(text=html)

        self.classify_and_write(current_url, response)

    def classify_and_write(self, url, response):
        text = ' '.join(response.css('::text').extract())
        words = re.findall(r'\b\w+\b', text.lower())

        casino_count = sum(word in words for word in casino)
        adult_count = sum(word in words for word in adult)

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