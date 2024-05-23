import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from scrapy.selector import Selector
from collections import deque, defaultdict
from urllib.parse import urlparse, urljoin, unquote
import re

casino = ["도박", "카지노", "또또", "로또", "환불", "포인트"]
adult = ["19", "유흥", "오피", "정화","한국", "야동", "BJ"]
class ReurlSpider(scrapy.Spider):
    name = "reurl44"
    start_urls = [
        "https://zzang4.com/"
    ]
    handle_httpstatus_list = [403]  # HTTP 403 상태 코드를 처리하도록 설정

    # 초기 세팅 함수
    def __init__(self, *args, **kwargs):
        super(ReurlSpider, self).__init__(*args, **kwargs)
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--remote-debugging-port=9223")  # 포트 설정
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.file = open('urls.txt', 'w')
        self.words_file = open('words_count.txt', 'w')
        self.depth_limit = 5  # 기본값으로 초기화

        # Class level queue and visited urls
        self.queue = deque([(url, 0) for url in self.start_urls])  # (url, depth)
        self.visited_urls = set(self.start_urls)  # 중복 확인을 위해 방문한 URL을 저장할 집합
        self.count_url = {urlparse(url).netloc: 1 for url in self.start_urls}  # 각 호스트에 대한 URL 개수 저장
        self.words_count = defaultdict(int)  # 단어 개수 저장

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(ReurlSpider, cls).from_crawler(crawler, *args, **kwargs)
        spider.depth_limit = crawler.settings.getint('DEPTH_LIMIT', 5)  # 설정에서 깊이 제한 읽기
        return spider

    # 초기 세팅, 큐에서 가져오고, 깊이 만큼 가져가기
    def start_requests(self):
        while self.queue:
            current_url, current_depth = self.queue.popleft()
            if current_depth <= self.depth_limit:
                yield scrapy.Request(current_url, self.parse, meta={'depth': current_depth})

    # 메인 시작
    def parse(self, response):
        # 오류 나면 그냥 끝내기
        if response.status == 403:
            self.log(f"Access denied to {response.url}")
            return

        current_depth = response.meta['depth']
        current_url = response.url

        self.driver.get(current_url)
        html = self.driver.page_source
        response = Selector(text=html)

        self.extract_and_queue_urls(response, current_url, current_depth)  # queue에서 url 추출하기
        self.extract_and_count_words(response)  # 단어 추출 및 개수 세기

        print(self.count_url)

    # url 큐에서 추출하기
    def extract_and_queue_urls(self, response, current_url, current_depth):
        # URL 추출
        get_urls = response.css('a::attr(href)').extract()
        get_onclick_urls = self.extract_onclick_urls()
        all_urls = get_urls + get_onclick_urls

        # http랑 https 통합하기
        for url in all_urls:
            if url.startswith('/'):
                url = urljoin(current_url, url)
            elif not url.startswith('http'):
                continue

            normalized_url = self.normalize_url(url)  # https로 싹 변환된 url rkwudhrl

            if normalized_url not in self.visited_urls:
                self.visited_urls.add(normalized_url)
                host = self.extract_host(normalized_url)
                self.count_url[host] = self.count_url.get(host, 0) + 1
                self.file.write(normalized_url + '\n')
                self.queue.append((normalized_url, current_depth + 1))

    # onclick 부분에서 url 추출하기
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

    # host 부분만 추출하기
    def extract_host(self, url):
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        return host

    # http를 https로 싹 바꾸기
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

    # 단어 추출 및 개수 세기
    def extract_and_count_words(self, response):
        text = ' '.join(response.css('::text').extract())
        words = re.findall(r'\b\w+\b', text.lower())
        word_count = defaultdict(int)
        for word in words:
            if word.strip():  # 공백만 있는 문자열 제거
                word_count[word] += 1

        print(word_count)

    def closed(self, reason):
        self.driver.quit()
        self.file.close()
        self.words_file.close()