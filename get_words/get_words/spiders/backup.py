import scrapy
from collections import deque
from scrapy.selector import Selector
import re

class GetwordsSpider(scrapy.Spider):
    name = "getwords2"
    # allowed_domains = ["www.naver.com"]
    # start_urls = ["https://www.naver.com"]

    def __init__(self, *args, **kwargs):
        super(GetwordsSpider, self).__init__(*args, **kwargs)
        self.divide_file = open('divide.txt', 'w')
        self.hosts_queue = deque(open('hosts.txt', 'r').read().strip().split("\n"))  # 호스트 파일에서 불러오기

    def start_requests(self):
        if self.hosts_queue:
            current_url = self.hosts_queue.popleft()
            yield scrapy.Request(url=current_url, callback=self.parse)

    def parse(self, response):
        current_url = response.url  # 현재 URL을 추출합니다.
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
            yield scrapy.Request(url=next_url, callback=self.parse)

    def extract_with_selenium(self, response):
        # Selenium을 이용한 텍스트 추출 로직 구현
        return []

    def extract_with_scrapy(self, response):
        texts = response.css('body *::text').getall()
        # 텍스트 리스트에서 공백 제거 및 정리
        cleaned_texts = [word for text in texts for word in self.clean_text(text)]
        return cleaned_texts

    def clean_text(self, text):
        text = re.sub(r'<(script|style).*?>.*?</\1>', '', text, flags=re.DOTALL)
        # 단어 단위로 분리
        words = re.findall(r'\b\w+\b', text)
        return words

    def extract_in_image(self, response):
        # 이미지에서 텍스트를 추출하는 로직 구현
        return []

    def extract_words_count(self, words):
        # 단어 개수 추출 로직 구현
        word_count = {}
        for word in words:
            word_count[word] = word_count.get(word, 0) + 1
        return word_count

    def save_words_count(self, url, count_words):
        # 단어 개수를 파일에 저장하는 로직 구현
        for word, count in count_words.items():
            self.divide_file.write(f"{url} ---> {word}: {count}\n")