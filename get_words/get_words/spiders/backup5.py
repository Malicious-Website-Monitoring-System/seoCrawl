import pytesseract
import re
import scrapy
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from scrapy.http import Request
from urllib.parse import urljoin
from collections import deque, Counter
from scrapy.selector import Selector  # 추가된 부분
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os

class GetwordsSpider(scrapy.Spider):
    name = "getwords55"
    custom_settings = {
        'REDIRECT_ENABLED': True
    }

    def __init__(self, *args, **kwargs):
        super(GetwordsSpider, self).__init__(*args, **kwargs)
        self.divide_file = open('divide.txt', 'w', encoding='utf-8')
        self.image_file = open('image.txt', 'w', encoding='utf-8')  # 이미지 단어를 기록할 파일 열기
        self.hosts_queue = deque(open('hosts.txt', 'r', encoding='utf-8').read().strip().split("\n"))

        self.logger.info(f"Loaded {len(self.hosts_queue)} URLs from hosts.txt")

        # Tesseract 경로 설정 (맥북용)
        pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'  # Tesseract 실행 파일 경로
        os.environ['TESSDATA_PREFIX'] = '/opt/homebrew/opt/tesseract/share/tessdata/'  # Tesseract 데이터 파일 경로

        #윈도우용
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    def start_requests(self):
        if self.hosts_queue:
            current_url = self.hosts_queue.popleft()
            self.logger.info(f"Starting request for {current_url}")
            yield scrapy.Request(url=current_url, callback=self.parse, errback=self.errback)

    def parse(self, response):
        current_url = response.url
        self.logger.info(f"Processing URL: {current_url}")

        texts = self.extract_with_scrapy(response)
        self.logger.debug(f"Scrapy extracted texts: {texts}")

        total_words = set(texts)
        self.logger.info(f"Total unique words from Scrapy: {len(total_words)}")

        if len(total_words) < 10:
            self.logger.info("Extracting additional texts with Selenium due to insufficient words.")
            texts.extend(self.extract_with_selenium(response))

        # 이미지 텍스트 추출 및 통합
        image_texts = list(self.extract_in_image(response, current_url))
        for future in image_texts:
            res = yield future
            if res and 'gettext' in res.meta:
                texts.extend(res.meta['gettext'])

        count_words = self.extract_words_count(texts)
        self.logger.info(f"Total words after combining: {len(count_words)}")
        self.save_words_count(current_url, count_words)

        if self.hosts_queue:
            next_url = self.hosts_queue.popleft()
            self.logger.info(f"Queueing next URL: {next_url}")
            yield scrapy.Request(url=next_url, callback=self.parse, errback=self.errback)

    # 셀레니움으로 전체 단어 추출하기(HTML)
    def extract_with_selenium(self, response):
        try:
            url = response.url
            options = Options()
            options.add_argument("headless")
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            # content 속성을 포함하는 모든 태그 찾기
            all_tags = driver.find_elements(By.XPATH, '//*[@content]')
            contents = [tag.get_attribute("content") for tag in all_tags]
            contents_words = []
            for content in contents:
                # 각 content에서 한글만 추출하기
                content_word = re.findall(r'[\uAC00-\uD7A3]+', content)
                contents_words.extend(content_word)

            # body 요소 가져오기
            body_element = driver.find_element(By.TAG_NAME, 'body')
            # body 요소 안에 있는 모든 텍스트 가져오기
            body_text = body_element.text
            # 단어만 추출하기
            body_words = re.findall(r'\b\w+\b', body_text)
            # 단어와 contents를 하나의 리스트로 합치기
            combined_list = body_words + contents_words

            return combined_list

        except Exception as e:
            # self.logger.error(f"An error occurred with {url}: {e}")
            return []

        finally:
            driver.quit()

    # 스크래피로 전체 단어 추출하기(HTML)
    def extract_with_scrapy(self, response):
        # 스크립트 및 스타일 태그 제거
        cleaned_html = re.sub(r'<(script|style).*?>.*?</\1>', '', response.text, flags=re.DOTALL)
        # 클린된 HTML로부터 텍스트 추출
        selector = Selector(text=cleaned_html)
        texts = selector.css('body *::text').getall()
        # 텍스트 리스트에서 공백 제거 및 정리
        cleaned_texts = [word for text in texts for word in self.clean_text(text)]
        return cleaned_texts

    # 단어 추출 시 단어단위로 분리하기
    def clean_text(self, text):
        # 단어 단위로 분리
        words = re.findall(r'\b\w+\b', text)
        return words

    # 이미지에서 단어 추출하는 코드
    def extract_in_image(self, response, current_url):
        self.image_file.write(f"{current_url}\n")
        img_urls = response.css('img::attr(src)').extract()
        for img_url in img_urls:
            if not img_url.startswith(('http', 'https')):
                img_url = urljoin(response.url, img_url)
            yield Request(img_url, callback=self.parse_image, meta={'img_url': img_url, 'current_url': current_url})

    def parse_image(self, response):
        img_url = response.meta['img_url']
        current_url = response.meta['current_url']
        self.logger.info(f"Processing image: {img_url}")

        try:
            img = Image.open(BytesIO(response.body))
            if img.format not in ['JPEG', 'PNG', 'GIF']:
                self.logger.error(f"Unsupported image format: {img.format}")
                return

            min_image_width = 50
            min_image_height = 50
            width, height = img.size

            if width > min_image_width and height > min_image_height:
                text = pytesseract.image_to_string(img, lang='kor+eng')
                gettext = self.process_text(text)
                if gettext:
                    self.image_file.write(f"{img_url} : {', '.join(gettext)}\n")
                    # Combine the extracted text directly here
                    current_texts = getattr(response.meta, 'gettext', [])
                    current_texts.extend(gettext)
                    response.meta['gettext'] = current_texts
                    return Request(url=current_url, callback=self.continue_parse, meta=response.meta, dont_filter=True)
            else:
                self.logger.info("Image too small to process")
        except Exception as e:
            self.logger.error(f"An error occurred while processing the image: {e}")
            return

    def continue_parse(self, response):
        # Continue processing the initial parse logic
        current_url = response.meta['current_url']
        texts = response.meta.get('gettext', [])
        count_words = self.extract_words_count(texts)
        self.logger.info(f"Total words after combining: {len(count_words)}")
        self.save_words_count(current_url, count_words)

    def process_text(self, text):
        text = re.sub(r'\b[ㄱ-ㅎㅏ-ㅣ]\b', '', text)
        text = re.sub('[0-9]', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'\s+', ' ', text)
        word_list = text.strip().split()
        cleaned_word_list = [re.sub(r'[ㄱ-ㅎㅏ-ㅣ]', '', word) for word in word_list]
        filtered = [word for word in cleaned_word_list if len(word) > 1]
        return filtered

    # 단어 개수 추출하기
    def extract_words_count(self, words):
        return dict(Counter(words))

    # 단어 개수 추출한 거 파일에 저장하기
    def save_words_count(self, url, count_words):
        self.logger.info(f"Saving word counts for URL: {url}")
        for word, count in count_words.items():
            self.divide_file.write(f"{url} ---> {word}: {count}\n")

    def errback(self, failure):
        self.logger.error(repr(failure))
        if self.hosts_queue:
            next_url = self.hosts_queue.popleft()
            self.logger.info(f"Queueing next URL after error: {next_url}")
            yield scrapy.Request(url=next_url, callback=self.parse, errback=self.errback)

    def closed(self, reason):
        self.divide_file.close()
        self.image_file.close()


