# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

import sqlite3
import openai
from scrapy.exceptions import NotConfigured
from .items import GetWordsItem


# class GetWordsPipeline:
#     def process_item(self, item, spider):
#         return item

class SQLitePipeline:

    def open_spider(self, spider):
        self.connection = sqlite3.connect('word_counts.db')
        self.cursor = self.connection.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host TEXT UNIQUE,
                classification TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS words_count (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host TEXT,
                redirect TEXT,
                words TEXT,
                count INTEGER,
                FOREIGN KEY (host) REFERENCES hosts (host)
            )
        ''')
        self.connection.commit()

    def close_spider(self, spider):
        self.connection.close()

    def process_item(self, item, spider):
        self.cursor.execute('INSERT OR IGNORE INTO hosts (host, classification) VALUES (?, ?)', (item['host'], None))
        self.cursor.execute('''
            INSERT INTO words_count (host, redirect, words, count)
            VALUES (?, ?, ?, ?)
        ''', (item['host'], item.get('redirect'), item['words'], item['count']))
        self.connection.commit()
        return item
    


#################


