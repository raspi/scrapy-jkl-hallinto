# -*- coding: utf-8 -*-
from urllib.parse import urlsplit, urlencode, unquote, urljoin
from urllib.parse import parse_qsl as queryparse

import scrapy
from scrapy import signals


class JklSpiderMiddleware(object):
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider: scrapy.Spider):
        return None

    def process_spider_output(self, response, result, spider: scrapy.Spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider: scrapy.Spider):
        pass

    def process_start_requests(self, start_requests, spider: scrapy.Spider):
        for r in start_requests:
            yield r

    def spider_opened(self, spider: scrapy.Spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class JklDownloaderMiddleware(object):
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request: scrapy.Request, spider: scrapy.Spider):
        return None

    def process_response(self, request: scrapy.Request, response, spider: scrapy.Spider):
        return response

    def process_exception(self, request: scrapy.Request, exception, spider: scrapy.Spider):
        pass

    def spider_opened(self, spider: scrapy.Spider):
        spider.logger.info('Spider opened: %s' % spider.name)
