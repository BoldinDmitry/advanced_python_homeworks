import asyncio
import json
import re

from aioelasticsearch import Elasticsearch
from aioelasticsearch import exceptions as elastic_exceptions
from aiohttp import ClientSession, TCPConnector
from bs4 import BeautifulSoup

import aio_pika
from dataclasses import dataclass
from final.settings import crawler_inbound, queue_host


@dataclass
class Link:
    link: str
    domain: str


class Crawler:
    LINKS = asyncio.Queue()
    LINKS_FOR_RPS = asyncio.Queue()

    ALREADY_WAS = set()
    LINKS_COUNTER = {}

    loop = None

    async def make_record_to_es(self, link, soup):
        cleaned_text = soup.get_text()
        doc = {"link": link.link, "body": cleaned_text}
        async with Elasticsearch(ingore=409) as es:
            try:
                self.LINKS_COUNTER[link.domain] += 1
                await es.create(
                    index="crawler_links", doc_type="crawler_links", id=link, body=doc
                )
                await es.close()
            except elastic_exceptions.ConflictError:
                pass

    async def fetch(self, session):
        url_obj = await self.LINKS.get()
        url = url_obj.link
        print(url)
        while self.LINKS_COUNTER[url_obj.domain] < 5:
            async with session.get(url) as response:
                body = await response.read()

                soup = BeautifulSoup(body, "html.parser")
                await self.make_record_to_es(url_obj, soup)

                for a in soup.findAll(
                        "a", attrs={"href": re.compile("^http?[s]://.*/$")}
                ):
                    link = a.attrs["href"]
                    if url_obj.domain in link and link not in self.ALREADY_WAS:
                        link_obj = Link(link=link, domain=url_obj.domain)
                        await self.LINKS_FOR_RPS.put(link_obj)
                        self.ALREADY_WAS.add(link)

    async def bound_fetch(self, sem, session):
        async with sem:
            return await self.fetch(session)

    async def rps_counter(self, rps):
        while True:
            url = await self.LINKS_FOR_RPS.get()
            await asyncio.sleep(1 / rps)
            await self.LINKS.put(url)

    async def get_tasks(self):
        connection = await aio_pika.connect_robust(
            queue_host, loop=self.loop
        )

        queue_name = crawler_inbound

        async with connection:
            channel = await connection.channel()

            queue = await channel.declare_queue(
                queue_name, auto_delete=True
            )

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        # TODO make Tasks classes support
                        task = json.loads(message.body)
                        domain = task["index"]["domain"]
                        self.LINKS_COUNTER[domain] = 0
                        await self.LINKS.put(Link(link="https://" + domain, domain=domain))

                        sem = asyncio.Semaphore(20)

                        connector = TCPConnector(verify_ssl=False)
                        async with ClientSession(connector=connector) as session:
                            tasks = []
                            for _ in range(5):
                                tasks.append(asyncio.ensure_future(self.bound_fetch(sem, session)))
                            await asyncio.gather(*tasks)

    async def run(self, rps):
        sem = asyncio.Semaphore(20)

        connector = TCPConnector(verify_ssl=False)
        async with ClientSession(connector=connector) as session:
            tasks = []
            for _ in range(5):
                tasks.append(asyncio.ensure_future(self.bound_fetch(sem, session)))

            asyncio.ensure_future(self.rps_counter(rps))
            asyncio.ensure_future(self.get_tasks())

            await asyncio.gather(*tasks)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    crawler = Crawler()
    crawler.loop = loop

    asyncio.ensure_future(crawler.run(3))
    loop.run_forever()
