from aioelasticsearch import Elasticsearch


async def search(q, limit=None, offset=0):
    async with Elasticsearch() as es:
        body = {"query": {"match": {"body": q}}}
        scan = await es.search(
            size=limit, from_=offset, index="_all", doc_type="crawler_links", body=body
        )
        docs = scan["hits"]["hits"]
        return [doc["_source"]["link"] for doc in docs]

