import scrapy
from collections import deque
from scrapy.selector import Selector
import re
from collections import Counter
from selenium import webdriver
from selenium.webdriver.common.by import By
from urllib.parse import urlparse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class GetwordsSpider(scrapy.Spider):
    name = "getwords222"
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
        current_url = response.url 
        # self.logger.info(f"Processing URL: {current_url}")
        texts = self.extract_with_scrapy(response)

        total_words = set(texts)
        
        if len(total_words) < 10:
            texts = self.extract_with_selenium(response)
        image_texts = yield from self.extract_in_image(response)
        texts.extend(image_texts)

        count_words = self.extract_words_count(texts)
        self.save_words_count(current_url, count_words)

        if self.hosts_queue:
            next_url = self.hosts_queue.popleft()
            self.logger.info(f"Queueing next URL: {next_url}")
            yield scrapy.Request(url=next_url, callback=self.parse, errback=self.errback)



##ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ##
    #셀레니움으로 전체 단어 추출하기(HTML) - 오정현
    def extract_with_selenium(self,response):
        try:
            url = response.url      
            options = Options()
            options.add_argument("headless")
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            # text말고도 속성값에도 유의미한 키워드들 포함한다고 생각
            # 예시 :  <meta name="description" content="무료웹툰 성인사이트 토렌트 링크모음과 무료 영화 TV 드라마 다시보기 주소모음을 소개하고 오피, 유흥, 스포츠중계 및 커뮤니티 사이트순위 정보를 제공합니다.">

            # content속성을 포함하는 모든 태그 찾기
            all_tags = driver.find_elements(By.XPATH, '//*[@content]')

            # 각 태그의 content 속성 값 가져오기
            contents = [tag.get_attribute("content") for tag in all_tags]
            contents_words=[]
            for content in contents:  
                # 각 content에서 한글만 추출하기 -> 영어까지 하면 'width' / 'index' / 'follow' / 'https', 'funbe384', 'com', 'EC', '9B', 'B9', 'ED', '88', 'B0' 등. 제외해도 될 것 같음
                content_word = re.findall(r'[\uAC00-\uD7A3]+', content)
                contents_words.extend(content_word)
            
            # body 요소 가져오기
            body_element = driver.find_element(By.TAG_NAME, 'body')

            # body 요소 안에 있는 모든 텍스트 가져오기
            body_text = body_element.text

            # 단어만 추출하기 #토토보증업체1BET1 이런거때문에 숫자도 포함
            body_words = re.findall(r'\b\w+\b', body_text)

            # 단어와 contents를 하나의 리스트로 합치기
            combined_list = body_words + contents_words
            
            return combined_list   # Counter(combined_list)     
            

        except Exception as e:
            print(f"An error occurred with {url}: {e}")
            return None
        
        finally:
            driver.quit()

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



##ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ##
    #이미지에서 단어 추출하는 코드(홍인혜)
    def extract_in_image(self, response):
            # 도메인의 이미지 가져오기
            img_urls = response.css('img::attr(src)').extract()

            # 이미지 불러오고 변수에 저장하기
            for img_url in img_urls:
                if not img_url.startswith(('http', 'https')):
                    img_url = urljoin(response.url, img_url)
                yield Request(img_url, callback=self.parse_image, errback=self.errback_image)

    def parse_image(self, response):

        try:
            #opencv랑 PIL중에 머가 좋지
            img = Image.open(BytesIO(response.body))

            # 너무 작은 아이콘은 거르기
            min_image_width = 50  # 최소 이미지 너비
            min_image_height = 50  # 최소 이미지 높이
            width, height = img.size

            if width > min_image_width and height > min_image_height:
                #이미지 전처리 함수 사용여부
                #img = self.clean_image(img)

                #tesseract사용, 영어 뽑으려면 kor+eng 하면 됨
                text = pytesseract.image_to_string(img, lang='kor')
                gettext = self.process_text(text)
                
                #1) 리스트에 저장
                self.get.extend(gettext)
                yield None
                
                #2) 아이템으로 넘기기
                #item = ProjectItem()
                #item['text'] = gettext
                #yield item

            yield None

        except IOError as e:
            yield None

    def errback_image(self, failure):
        yield None

    #적절한 노이즈 제거 방법을 찾기!!!!!!!!!!!!!!
    def clean_image(self, image):
        #opencv사용을 위해 쓰기
        img_cv2 = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    def process_text(self, text):

        text = re.sub(r'\b[ㄱ-ㅎㅏ-ㅣ]\b', '', text)
        text = re.sub('[a-zA-Z0-9]', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'\s+', ' ', text)

        word_list = text.strip().split()
        cleaned_word_list = [re.sub(r'[ㄱ-ㅎㅏ-ㅣ]', '', word) for word in word_list]

        filtered = [word for word in cleaned_word_list if len(word) > 1]
        return filtered
    

##ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ##





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