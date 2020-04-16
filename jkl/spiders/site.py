# -*- coding: utf-8 -*-
import os
import pathlib
import re
from urllib.parse import urlsplit, urlencode, unquote, urljoin
from urllib.parse import parse_qsl as queryparse
import scrapy
from scrapy.utils.response import open_in_browser

from jkl.items import *

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


class BaseSpider(scrapy.Spider):
    name = ''
    allowed_domains = [
        'jkl.fi',
        'julkinen.jkl.fi',
    ]

    def parse(self, response: scrapy.http.response):
        raise NotImplementedError

    def parse_bid(self, response: scrapy.http.Response):
        rq = dict(queryparse(urlsplit(response.url).query))

        for link in response.xpath("//a"):
            href = link.xpath("./@href").get()
            q = dict(queryparse(urlsplit(href).query))
            if not q:
                continue

            if ('doctype' in q) or ('docid' in q):
                yield scrapy.Request(
                    response.urljoin(href),
                    meta={
                        "name": response.meta["name"],
                        "id": rq[' bid'],
                    },
                    callback=self.dl_doc,
                )

    def get_filename(self, response: scrapy.http.Response):
        fname = urlsplit(response.url).query + ".pdf"
        cd = response.headers.get("Content-Disposition").decode("utf8")

        findstr = "filename="
        fpos = cd.find(findstr)
        if fpos != -1:
            fpos += len(findstr)
            fname = unquote(cd[fpos:])
            fname = fname.replace("_", " ")

        return fname

    def dl_doc(self, response: scrapy.http.Response):
        """
        Download PDF/xls etc files
        """
        fname = self.get_filename(response)
        fpath = os.path.join(CURRENT_PATH, "..", "..", "items", self.name, response.meta["name"], response.meta["id"],
                             fname)

        pathlib.Path(os.path.dirname(fpath)).mkdir(parents=True, exist_ok=True)

        with open(fpath, "wb") as f:
            f.write(response.body)
            self.logger.info(f"saved {fpath}")

    def build_form(self, form: scrapy.selector.SelectorList) -> dict:
        reqobj = {}

        labels = []
        for label in form.xpath(".//label"):
            labels.append({
                "descr": label.xpath("./text()").get(),
                "id": label.xpath("./@for").get(),
            })

        for input in form.xpath(".//input"):
            inname = input.xpath("./@name").get()
            invalue = input.xpath("./@value").get()
            if invalue is None:
                invalue = ""

            reqobj[inname] = invalue

        for findid in labels:
            found = form.xpath(f".//*[@id='{findid['id']}']")
            if found is None:
                continue
            found = found[0]

            tag = found.root.tag
            name = found.xpath("./@name").get()

            if tag == "select":
                opts = []
                for option in found.xpath("./option"):
                    opts.append({
                        "name": option.xpath("./text()").get().strip(),
                        "value": option.xpath("./@value").get().strip(),
                    })

                reqobj[name] = opts

        return reqobj


class CommonSpider(BaseSpider):
    name = ''

    def parse(self, response: scrapy.http.Response):
        findform = response.xpath("//form[@name='form1']")
        form = self.build_form(findform)

        if "kirjaamo" not in form:
            raise ValueError("kirjaamo not found")

        if not isinstance(form["kirjaamo"], list):
            raise ValueError("kirjaamo is not list")

        method = findform.xpath("./@method").get()
        action = response.urljoin(findform.xpath("./@action").get())

        alist = form["kirjaamo"]
        del form["kirjaamo"]

        for param in alist:
            val = param["value"]
            if val == "":
                continue

            fdata = form
            fdata["kirjaamo"] = val

            yield scrapy.FormRequest(
                action,
                method=method,
                formdata=fdata,
                meta={
                    "name": param["name"],
                    "dont_cache": True,
                },
                callback=self.parse_search_result,
            )

    def parse_search_result(self, response: scrapy.http.Response):
        for link in response.xpath("//a"):
            href = link.xpath("./@href").get()
            q = dict(queryparse(urlsplit(href).query))
            if not q:
                continue

            if ' bid' in q:
                yield scrapy.Request(
                    response.urljoin(href),
                    meta={
                        "name": response.meta["name"],
                        "dont_cache": True,
                    },
                    callback=self.parse_bid,
                )


class PoytakirjaSpider(CommonSpider):
    name = 'poytakirjat'
    start_urls = [
        'http://julkinen.jkl.fi:8082/ktwebbin/dbisa.dll/ktwebscr/pk_tek_tweb.htm',
    ]


class EsityslistaSpider(CommonSpider):
    name = 'esityslistat'
    start_urls = [
        'http://julkinen.jkl.fi:8082/ktwebbin/dbisa.dll/ktwebscr/epj_tek_tweb.htm',
    ]


class VHPaatoksetSpider(BaseSpider):
    name = 'vhpaatokset'
    start_urls = [
        'http://julkinen.jkl.fi:8082/ktwebbin/dbisa.dll/ktwebscr/vparhaku_tweb.htm',
    ]

    def parse(self, response: scrapy.http.response):
        findform = response.xpath("//form[@name='form1']")
        form = self.build_form(findform)

        if "vin" not in form:
            raise ValueError("vin not found")

        if not isinstance(form["vin"], list):
            raise ValueError("vin is not list")

        method = findform.xpath("./@method").get()
        action = response.urljoin(findform.xpath("./@action").get())

        alist = form["vin"]
        del form["vin"]

        form["1009_2606"] = ""
        form["1009_2615"] = ""
        form["text"] = ""
        form["orderby"] = "6 desc,5 desc"
        form["maxrows"] = "50"

        for param in alist:
            val = param["value"]
            if val == "":
                continue

            fdata = form
            fdata["vin"] = val

            yield scrapy.FormRequest(
                action,
                method=method,
                formdata=fdata,
                meta={
                    "name": param["name"],
                    "dont_cache": True,
                },
                callback=self.parse_search_result,
            )

    def parse_search_result(self, response: scrapy.http.Response):
        tbl = response.xpath("//table[@class='table table-striped table-hover table-bordered']")
        for rowidx, row in enumerate(tbl.xpath("./tr")):
            if rowidx == 0:
                continue

            obj = {}

            for idx, col in enumerate(row.xpath("./td")):
                if idx == 0:
                    rawdate = "".join(col.xpath("./text()").getall()).strip()
                    rawdate = ' '.join(rawdate.split())
                    rawdate = rawdate.strip()

                    rem = re.split(r"^(\d+)\s+/(\d+) (\d+)\.(\d+)\.(\d+)$", rawdate)[1:]
                    rem.pop()

                    vhnum, vhyear, pday, pmonth, pyear = rem
                    obj["date"] = f"{vhyear}-{vhnum.zfill(3)}__{pyear}-{pmonth.zfill(2)}-{pday.zfill(2)}"
                elif idx == 1:
                    for link in col.xpath("./a"):
                        txt = link.xpath("./text()").get().strip()
                        url = response.urljoin(link.xpath("./@href").get())
                        if txt == '0 kpl':
                            continue

                        if 'title' not in obj:
                            obj["title"] = txt
                            obj["link"] = url
                        else:
                            obj["attach"] = url

            dirpath = os.path.join(self.name, )

            if "attach" in obj:
                yield scrapy.Request(
                    obj["attach"],
                    meta={
                        "name": response.meta["name"],
                        "id": obj["date"],
                    },
                    callback=self.parse_attachments,
                )

            yield scrapy.Request(
                obj["link"],
                meta={
                    "name": response.meta["name"],
                    "id": obj["date"],
                },
                callback=self.dl_doc,
            )

    def parse_attachments(self, response: scrapy.http.Response):
        for link in response.xpath("//a"):
            href = link.xpath("./@href").get()
            q = dict(queryparse(urlsplit(href).query))
            if not q:
                continue

            if ('doctype' in q) or ('docid' in q):
                yield scrapy.Request(
                    response.urljoin(href),
                    meta={
                        "name": response.meta["name"],
                        "id": response.meta["id"],
                    },
                    callback=self.dl_doc,
                )
