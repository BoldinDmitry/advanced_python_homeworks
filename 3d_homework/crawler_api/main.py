from aioelasticsearch import Elasticsearch
from aiohttp import web


async def handle(request):
    q = request.query.get("q")
    if q is None:
        error_message = {"error": "No q parameter"}
        return web.json_response(error_message, status=400)

    try:
        limit = int(request.query.get("limit", -1))
        offset = int(request.query.get("offset", 0))
    except ValueError as e:
        error_message = {"error": e.args[0]}
        return web.json_response(error_message)

    links = await search(q, limit, offset)

    return web.json_response(links)


async def search(q, limit=None, offset=0):
    async with Elasticsearch() as es:
        body = {"query": {"match": {"body": q}}}
        scan = await es.search(
            size=limit, from_=offset, index="_all", doc_type="crawler_links", body=body
        )
        print(scan)
        docs = scan["hits"]["hits"]
        return [doc["_source"]["link"] for doc in docs]


app = web.Application()
app.add_routes([web.get("/api/v1/search/", handle)])

web.run_app(app)
