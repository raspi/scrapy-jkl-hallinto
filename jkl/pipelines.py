# -*- coding: utf-8 -*-
import scrapy


class JklPipeline(object):
    def process_item(self, item: scrapy.Item, spider: scrapy.Spider):
        return item
