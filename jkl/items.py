# -*- coding: utf-8 -*-

import scrapy


class JklDocItem(scrapy.Item):
    id = scrapy.Field()
    body = scrapy.Field()
    name = scrapy.Field()
