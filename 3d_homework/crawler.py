import asyncio
import re

from aioelasticsearch import Elasticsearch
from aioelasticsearch import exceptions as elastic_exceptions
from aiohttp import ClientSession, TCPConnector
from bs4 import BeautifulSoup


class Crawler:
    START_URL = "https://habr.com/ru/"
    DOMAIN = "habr.com"

    LINKS = asyncio.Queue()
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
            url = await self.LINKS.get()
            async with session.get(url) as response:
                body = await response.read()

                soup = BeautifulSoup(body, "html.parser")
                await self.make_record_to_es(url, soup)

                for a in soup.findAll(
                    "a", attrs={"href": re.compile("^http?[s]://.*/$")}
                ):
                    link = a.attrs["href"]
                    if self.DOMAIN in link and link not in self.ALREADY_WAS:
                        await self.LINKS.put(link)
                        self.ALREADY_WAS.append(link)

    async def bound_fetch(self, sem, session):
        async with sem:
            return await self.fetch(session)

    async def run(self, rps):
        await self.LINKS.put(self.START_URL)

        sem = asyncio.Semaphore(20)

        connector = TCPConnector(limit=rps, verify_ssl=False)

        async with ClientSession(connector=connector) as session:

            tasks = []
            for _ in range(5):
                task = asyncio.ensure_future(self.bound_fetch(sem, session))
                tasks.append(task)

            responses = asyncio.gather(*tasks)
            await responses


loop = asyncio.get_event_loop()

crawler = Crawler()

future = asyncio.ensure_future(crawler.run(3))
loop.run_until_complete(future)
