from aioelasticsearch import Elasticsearch
from aioelasticsearch.helpers import Scan
from aiohttp import web


async def handle(request):
    q = request.query.get("q")
    limit = request.query.get("limit")
    offset = request.query.get("offset")
    if q is None:
        return web.Response(text="No q parameter", status=400)

    links = await search(q, limit, offset)

    return web.json_response(links)


async def search(q, limit=None, offset=None):
    async with Elasticsearch() as es:
        body = {"query": {"match": {"body": q}}}
        async with Scan(es, index="_all", doc_type="crawler_links", query=body) as scan:
            return await split_docs(scan, limit, offset)


async def split_docs(scan, limit, offset):
    links = [doc["_source"]["link"] async for doc in scan]

    if offset is None:
        offset = 0
    else:
        offset = int(offset)

    count = len(links)

    if limit is None:
        limit = count
    else:
        limit = int(limit)

    start = min(count, offset)
    end = min(limit + start, count)

    return links[start:end]


async def transform_results(scan, offset=0, limit=None):
    res_source = [{**i["_source"]} async for i in scan]
    count = len(res_source)

    if limit:
        return res_source[offset: min(limit + offset, count)], count

    return res_source[offset:], count


app = web.Application()
app.add_routes([web.get("/api/v1/search/", handle)])

web.run_app(app)
