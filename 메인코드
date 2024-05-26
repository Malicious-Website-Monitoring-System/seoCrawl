import scrapy
from collections import deque
from scrapy.selector import Selector
import re

class GetwordsSpider(scrapy.Spider):
    name = "getwords"
    # allowed_domains = ["www.naver.com"]
    # start_urls = ["https://www.naver.com"]

    def __init__(self, *args, **kwargs):
        super(GetwordsSpider, self).__init__(*args, **kwargs)
        self.divide_file = open('divide.txt', 'w')
        self.hosts_queue = deque(open('hosts.txt', 'r').read().strip().split("\n"))  # 호스트 파일에서 불러오기
        self.logger.info(f"Loaded {len(self.hosts_queue)} URLs from hosts.txt")

    def start_requests(self):
        if self.hosts_queue:
            current_url = self.hosts_queue.popleft()
            self.logger.info(f"Starting request for {current_url}")
            yield scrapy.Request(url=current_url, callback=self.parse, errback=self.errback)

    def parse(self, response):
        current_url = response.url  # 현재 URL을 추출합니다.
        self.logger.info(f"Processing URL: {current_url}")
        texts = self.extract_with_scrapy(response)

        total_words = set(texts)
        
        if len(total_words) < 10:
            texts = self.extract_with_selenium(response)

        image_texts = self.extract_in_image(response)
        texts.extend(image_texts)

        count_words = self.extract_words_count(texts)
        self.save_words_count(current_url, count_words)

        if self.hosts_queue:
            next_url = self.hosts_queue.popleft()
            self.logger.info(f"Queueing next URL: {next_url}")
            yield scrapy.Request(url=next_url, callback=self.parse, errback=self.errback)


    #셀레니움으로 전체 단어 추출하기(HTML)
    def extract_with_selenium(self, response):
        # Selenium을 이용한 텍스트 추출 로직 구현
        return []

    #스크립트로 전체 단어 추출하기(HTML)
    def extract_with_scrapy(self, response):
        # 스크립트 및 스타일 태그 제거
        cleaned_html = re.sub(r'<(script|style).*?>.*?</\1>', '', response.text, flags=re.DOTALL)
        # 클린된 HTML로부터 텍스트 추출
        selector = Selector(text=cleaned_html)
        texts = selector.css('body *::text').getall()
        # 텍스트 리스트에서 공백 제거 및 정리
        cleaned_texts = [word for text in texts for word in self.clean_text(text)]
        
        # 디버깅: 추출된 텍스트 확인
        for text in cleaned_texts:
            self.logger.debug(f"Extracted text: {text}")
        
        return cleaned_texts

    #단어 추출 시 단어단위로 분리하기(script등의 단어 제거)
    def clean_text(self, text):
        # 단어 단위로 분리
        words = re.findall(r'\b\w+\b', text)
        return words


    #이미지에서 단어 추출하는 코드(홍인혜)
    def extract_in_image(self, response):
        # 이미지에서 텍스트를 추출하는 로직 구현
        return []
    

    #단어 개수 추출하기(서민재)
    def extract_words_count(self, words):
        # 단어 개수 추출 로직 구현
        word_count = {}
        for word in words:
            word_count[word] = word_count.get(word, 0) + 1
        return word_count


    # 단어 개수 추출한 거 파일에 저장하기 (서민재))
    def save_words_count(self, url, count_words):
        self.logger.info(f"Saving word counts for URL: {url}")
        for word, count in count_words.items():
            self.divide_file.write(f"{url} ---> {word}: {count}\n")

    def errback(self, failure):
        # 에러 처리 및 로그 기록
        self.logger.error(repr(failure))
        if self.hosts_queue:
            next_url = self.hosts_queue.popleft()
            self.logger.info(f"Queueing next URL after error: {next_url}")
            yield scrapy.Request(url=next_url, callback=self.parse, errback=self.errback)
