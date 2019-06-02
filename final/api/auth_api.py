import asyncio
import json

import aio_pika

from final.settings import auth_inbound, auth_outbound, queue_host


async def request_response(request_query):

    loop = asyncio.get_event_loop()

    connection = await aio_pika.connect_robust(
        queue_host, loop=loop)

    async with connection:
        routing_key = auth_inbound

        channel = await connection.channel()

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(request_query).encode()
            ),
            routing_key=routing_key
        )

    connection = await aio_pika.connect_robust(
        queue_host, loop=loop)

    channel = await connection.channel()

    queue = await channel.declare_queue(
        auth_outbound, auto_delete=True
    )

    await asyncio.sleep(1)

    auth_answer = await queue.get(timeout=15)
    return auth_answer.body


async def signup(name, email, password):
    request_query = {"task": "signup", "data": {"name": name, "email": email, "password": password}}
    return await request_response(request_query)


async def login(email, password):
    request_query = {"task": "login", "data": {"email": email, "password": password}}
    return await request_response(request_query)
