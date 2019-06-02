import json

from final.api.auth_api import signup, login
from final.api.elastic_search_api import search

from aiohttp import web

routes = web.RouteTableDef()


async def search_view(request):
    q = request.query.get("q")
    if q is None:
        error_message = {"status": "bad_request", "data": ["no q parameter"]}
        return web.json_response(error_message, status=400)

    try:
        limit = int(request.query.get("limit", -1))
        offset = int(request.query.get("offset", 0))
    except ValueError as e:
        error_message = {"status": "bad_request", "data": [e.args[0]]}
        return web.json_response(error_message)

    links = await search(q, limit, offset)

    return web.json_response(links)


async def signup_view(request):
    data = await request.post()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if name is None or email is None or password is None:
        error_message = {"status": "bad_request", "data": {"name": name, "email": email, "password": password}}
        return web.json_response(error_message, status=400)

    signup_answer = await signup(name=name, email=email, password=password)
    json_ans = json.loads(signup_answer)

    if json_ans["status"] == "error":
        return web.json_response(json_ans, status=409)

    data = await login(email, password)

    response = {"status": "ok", "data": json.loads(data)}

    return web.json_response(response)


async def login_view(request):
    data = await request.post()
    email = data.get("email")
    password = data.get("password")

    if email is None or password is None:
        error_message = {"status": "bad_request", "data": {"email": email, "password": password}}
        return web.json_response(error_message, status=400)

    data = await login(email, password)

    response = {"status": "ok", "data": json.loads(data)}

    return web.json_response(response)
