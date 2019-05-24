import asyncio
import re

from asyncio import TimeoutError
from aioelasticsearch import Elasticsearch
from aioelasticsearch import exceptions as elastic_exceptions
from aiohttp import ClientSession, TCPConnector
from bs4 import BeautifulSoup
from dataclasses import dataclass


@dataclass
class Link:
    link: str
    errors_count: int


class Crawler:
    START_URL = "https://habr.com/ru/"
    DOMAIN = "habr.com"

    LINKS = asyncio.Queue()
    LINKS_FOR_RPS = asyncio.Queue()

    ALREADY_WAS = []
    LINKS_COUNTER = 0

    async def make_record_to_es(self, link, soup):
        cleaned_text = soup.get_text()
        doc = {"link": link, "body": cleaned_text}
        async with Elasticsearch(ingore=409) as es:
            try:
                await es.create(
                    index="crawler_links", doc_type="crawler_links", id=link, body=doc
                )
                await es.close()
                self.LINKS_COUNTER += 1
            except elastic_exceptions.ConflictError:
                pass

    async def fetch(self, session):
        while self.LINKS_COUNTER < 1000:
            url_obj = await self.LINKS.get()
            url = url_obj.link
            try:
                async with session.get(url, timeout=1) as response:
                    body = await response.read()

                    soup = BeautifulSoup(body, "html.parser")
                    await self.make_record_to_es(url, soup)

                    for a in soup.findAll(
                            "a", attrs={"href": re.compile("^http?[s]://.*/$")}
                    ):
                        link = a.attrs["href"]
                        if self.DOMAIN in link and link not in self.ALREADY_WAS:
                            link_obj = Link(link=link, errors_count=0)
                            await self.LINKS_FOR_RPS.put(link_obj)
                            self.ALREADY_WAS.append(link)
            except TimeoutError:
                print("error")
                if url_obj.errors_count > 1:
                    pass
                else:
                    url_obj.errors_count += 1
                    await self.LINKS_FOR_RPS.put(url_obj)

    async def bound_fetch(self, sem, session):
        async with sem:
            return await self.fetch(session)

    async def rps_counter(self, rps):
        while True:
            url = await self.LINKS_FOR_RPS.get()

            await asyncio.sleep(1 / rps)
            await self.LINKS.put(url)

    async def run(self, rps):
        await self.LINKS.put(Link(link=self.START_URL, errors_count=0))

        sem = asyncio.Semaphore(20)

        connector = TCPConnector(verify_ssl=False)

        async with ClientSession(connector=connector) as session:
            tasks = []

            for _ in range(5):
                tasks.append(asyncio.ensure_future(self.bound_fetch(sem, session)))

            tasks.append(asyncio.ensure_future(self.rps_counter(rps)))

            responses = asyncio.gather(*tasks)
            await responses


loop = asyncio.get_event_loop()

crawler = Crawler()

future = asyncio.ensure_future(crawler.run(3))
loop.run_until_complete(future)
