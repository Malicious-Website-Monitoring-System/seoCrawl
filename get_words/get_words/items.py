# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class GetWordsItem(scrapy.Item):
    host = scrapy.Field()
    redirect = scrapy.Field()
    words = scrapy.Field()
    count = scrapy.Field()

