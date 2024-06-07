import pytesseract
import re
import scrapy
from io import BytesIO
from PIL import Image
from scrapy.http import Request
from urllib.parse import urljoin
from collections import deque, Counter
from scrapy.selector import Selector
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os
from get_words.items import GetWordsItem

class GetwordsSpider(scrapy.Spider):
    name = "getwords1111"

    # 초깃값 설정
    def __init__(self, *args, **kwargs):
        super(GetwordsSpider, self).__init__(*args, **kwargs)
        # self.divide_file = open('divide.txt', 'w', encoding='utf-8') #단어 추출이 잘 되었는지 확인하기 위함
        self.image_file = open('image.txt', 'w', encoding='utf-8') #이미지 추출이 잘 되었는지 확인하기 위함
        self.hosts_queue = deque(open('hosts.txt', 'r', encoding='utf-8').read().strip().split("\n")) #hosts.txt에서 값을 불러와서 큐에 넣기

        #맥용 테서렉트 경로
        pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
        os.environ['TESSDATA_PREFIX'] = '/opt/homebrew/opt/tesseract/share/tessdata/'

        #윈도우용 테서렉트 경로
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'



    #스크래피 첫 시작시
    def start_requests(self):
        if self.hosts_queue:  #큐가 비어있지 않다면 
            current_url = self.hosts_queue.popleft() #맨 앞에서 시작
            yield scrapy.Request(url=current_url, callback=self.parse, errback=self.errback, dont_filter=True, meta={'original_url': current_url})

    def parse(self, response):
        original_url = response.meta.get('original_url') #큐에서 가져온 오리지널 경로
        redirected_url = response.url #반응하는 리다이렉트 경로

        texts = self.extract_with_scrapy(response) #스크래피로부터 단어 추출
        total_words = set(texts) #단어 개수 세기 위하여(중복 제거)

        if len(total_words) < 10: #x개 미만이라면
            texts.extend(self.extract_with_selenium(response)) #셀레니움으로 다시 체크

        #이미지로부터 글씨 뽑아오기
        image_texts = list(self.extract_in_image(response, original_url)) #리스트형태로 이미지에서 글씨 뽑아오기
        for future in image_texts:
            res = yield future
            if res and 'gettext' in res.meta:
                texts.extend(res.meta['gettext'])

        count_words = self.extract_words_count(texts)

        for word, count in count_words.items():
            item = GetWordsItem()
            item['host'] = original_url
            item['redirect'] = redirected_url if redirected_url != original_url else None
            item['words'] = word
            item['count'] = count
            yield item

        if self.hosts_queue:
            next_url = self.hosts_queue.popleft()
            yield scrapy.Request(url=next_url, callback=self.parse, errback=self.errback, dont_filter=True, meta={'original_url': next_url})

    def extract_with_selenium(self, response):
        try:
            url = response.url
            options = Options()
            options.add_argument("headless")
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            all_tags = driver.find_elements(By.XPATH, '//*[@content]')
            contents = [tag.get_attribute("content") for tag in all_tags]
            contents_words = []
            for content in contents:
                content_word = re.findall(r'[\uAC00-\uD7A3]+', content)
                contents_words.extend(content_word)

            body_element = driver.find_element(By.TAG_NAME, 'body')
            body_text = body_element.text
            body_words = re.findall(r'\b\w+\b', body_text)
            combined_list = body_words + contents_words

            return combined_list

        except Exception as e:
            return []

        finally:
            driver.quit()

    def extract_with_scrapy(self, response):
        cleaned_html = re.sub(r'<(script|style).*?>.*?</\1>', '', response.text, flags=re.DOTALL)
        selector = Selector(text=cleaned_html)
        texts = selector.css('body *::text').getall()
        cleaned_texts = [word for text in texts for word in self.clean_text(text)]
        return cleaned_texts

    def clean_text(self, text):
        words = re.findall(r'\b\w+\b', text)
        return words

        # 이미지에서 단어 추출하는 코드
    def extract_in_image(self, response, original_url):
        self.image_file.write(f"{original_url}\n")
        #수정: src 속성은 이미지를 즉시 로드하여 표시하는 데 사용되고, data-original 속성은 이미지를 나중에 필요할 때 로드하는 데 사용
        img_urls = response.css('img::attr(src), img::attr(data-original), img::attr(data-src)').extract()
        print(img_urls, len(img_urls))
        for img_url in img_urls:
            if not img_url.startswith(('http', 'https')):
                img_url = urljoin(response.url, img_url)
            yield Request(img_url, callback=self.parse_image, meta={'img_url': img_url, 'original_url': original_url})

    def parse_image(self, response):
        img_url = response.meta['img_url']
        original_url = response.meta['original_url']

        try:
            img = Image.open(BytesIO(response.body))
            if img.format not in ['JPEG', 'PNG', 'GIF']:
                return

            min_image_width = 50
            min_image_height = 50
            width, height = img.size

            if width > min_image_width and height > min_image_height:
                #수정: gif파일일 경우 마지막 프레임만 추출하기(대략적인 내용은 마지막에만 담겨있음)
                if img.format == 'GIF':
                    frames = ImageSequence.Iterator(img)
                    for frame in frames:
                        last_frame = frame
                    text = pytesseract.image_to_string(last_frame, lang='kor+eng')
                else:
                    text = pytesseract.image_to_string(img, lang='kor+eng')

                gettext = self.process_text(text)
                if gettext:
                    self.image_file.write(f"{img_url} : {', '.join(gettext)}\n")
                    count_words = self.extract_words_count(gettext)

                    for word, count in count_words.items():
                        item = GetWordsItem()
                        item['host'] = original_url
                        item['redirect'] = None
                        item['words'] = word
                        item['count'] = count
                        yield item
        except Exception as e:
            return

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

    def extract_words_count(self, words):
        return dict(Counter(words))

    def errback(self, failure):
        if self.hosts_queue:
            next_url = self.hosts_queue.popleft()
            yield scrapy.Request(url=next_url, callback=self.parse, errback=self.errback, dont_filter=True, meta={'original_url': next_url})

    def closed(self, reason):
        self.divide_file.close()
        self.image_file.close()
