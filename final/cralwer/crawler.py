import asyncio
import json
import re
import time
from datetime import datetime, timedelta

import aiosqlite
from aioelasticsearch import Elasticsearch
from aioelasticsearch import exceptions as elastic_exceptions
from aiohttp import ClientSession, TCPConnector
from bs4 import BeautifulSoup

import aio_pika
from dataclasses import dataclass
from final.orm import fields
from final.orm.models import Model
from final.orm.query_sets import QuerySet
from final.settings import crawler_inbound, database_file_path, queue_host


class CrawlerStats(Model):
    domain = fields.StringField()
    author_id = fields.IntField()
    https = fields.BoolField()
    time = fields.DateTimeField()
    pages_count = fields.IntField()
    avg_time_per_page = fields.FloatField()
    max_time_per_page = fields.FloatField()
    min_time_per_page = fields.FloatField()

    class Meta:
        table_name = "CrawlerStats"


@dataclass
class Link:
    link: str
    domain: str


class Crawler:
    loop = None

    LINKS = asyncio.Queue()
    LINKS_FOR_RPS = asyncio.Queue()

    ALREADY_WAS = set()

    LINKS_COUNTER = {}
    TIME_COUNTER = {}

    MAX_LINKS = {}

    AUTHORS = {}
    HTTPS = {}

    async def make_record_to_es(self, link, soup):
        cleaned_text = soup.get_text()
        doc = {"link": link.link, "body": cleaned_text}
        async with Elasticsearch(ingore=409) as es:
            self.LINKS_COUNTER[link.domain] += 1
            try:
                await es.create(
                    index="crawler_links", doc_type="crawler_links", id=link, body=doc
                )
                await es.close()
            except elastic_exceptions.ConflictError:
                pass

    async def fetch(self, session):
        while True:
            url_obj = await self.LINKS.get()
            url = url_obj.link

            if self.HTTPS[url_obj.domain] is None:
                continue

            while self.LINKS_COUNTER[url_obj.domain] < self.MAX_LINKS[url_obj.domain]:
                request_time = time.time()
                async with session.get(url) as response:
                    body = await response.read()

                    self.TIME_COUNTER[url_obj.domain].append(time.time() - request_time)

                    soup = BeautifulSoup(body, "html.parser")
                    await self.make_record_to_es(url_obj, soup)

                    if self.HTTPS[url_obj.domain]:
                        links = soup.findAll("a", attrs={"href": re.compile("^http?[s]://.*/$")})
                    else:
                        links = soup.findAll("a", attrs={"href": re.compile("^http://.*/$")})

                    for a in links:
                        link = a.attrs["href"]
                        if url_obj.domain in link and link not in self.ALREADY_WAS:
                            link_obj = Link(link=link, domain=url_obj.domain)
                            await self.LINKS_FOR_RPS.put(link_obj)
                            self.ALREADY_WAS.add(link)

            domain = url_obj.domain
            crawler_stats = CrawlerStats(
                domain=domain,
                author_id=self.AUTHORS[domain],
                https=self.HTTPS[domain],
                time=datetime.now(),
                pages_count=self.MAX_LINKS[domain],
                avg_time_per_page=sum(self.TIME_COUNTER[domain]) / self.MAX_LINKS[domain],
                max_time_per_page=max(self.TIME_COUNTER[domain]),
                min_time_per_page=min(self.TIME_COUNTER[domain])
            )

            if self.HTTPS[url_obj.domain] is None:
                continue

            await crawler_stats.save()

            self.HTTPS[domain] = None

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

                        all_stats = await CrawlerStats.objects.filter(domain=domain).get()
                        all_stats = filter(lambda x: x.time, all_stats)
                        last_stat = next(all_stats, None)

                        if last_stat is not None and last_stat.time < datetime.now() + timedelta(hours=1):
                            continue

                        self.LINKS_COUNTER[domain] = 0
                        self.TIME_COUNTER[domain] = []
                        self.MAX_LINKS[domain] = task["index"]["pages_count"]
                        self.AUTHORS[domain] = task["index"]["author_id"]
                        self.HTTPS[domain] = task["index"]["author_id"]

                        await self.LINKS.put(Link(link="https://" + domain, domain=domain))

    async def run(self, rps):
        QuerySet.loop = self.loop
        QuerySet.conn = await aiosqlite.connect(database_file_path, loop=self.loop)

        Model.loop = self.loop
        Model.conn = await aiosqlite.connect(database_file_path, loop=self.loop)

        event = asyncio.Event(loop=self.loop)

        sem = asyncio.Semaphore(20)

        connector = TCPConnector(verify_ssl=False)
        async with ClientSession(connector=connector) as session:
            for _ in range(5):
                self.loop.create_task(self.bound_fetch(sem, session))

            self.loop.create_task(self.rps_counter(rps))
            get_task_event = asyncio.create_task(self.get_tasks())
            event.set()
            await get_task_event


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    crawler = Crawler()
    crawler.loop = loop

    asyncio.ensure_future(crawler.run(3))
    loop.run_forever()
