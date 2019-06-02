import asyncio
import json

import aio_pika
import aiosqlite

from final.authorization.tasks import SignUp, LogIn
from final.orm.models import Model
from final.orm.query_sets import QuerySet
from final.settings import auth_inbound, auth_outbound, database_file_path, queue_host


class Authorization:
    loop = None

    async def send_response(self, response):
        connection = await aio_pika.connect_robust(
            queue_host, loop=self.loop)

        async with connection:
            routing_key = auth_outbound

            channel = await connection.channel()

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(response).encode()
                ),
                routing_key=routing_key
            )
            print(response)

    async def get_tasks(self):
        QuerySet.loop = self.loop
        QuerySet.conn = await aiosqlite.connect(database_file_path, loop=self.loop)

        Model.loop = self.loop
        Model.conn = await aiosqlite.connect(database_file_path, loop=self.loop)

        connection = await aio_pika.connect_robust(
            queue_host, loop=self.loop
        )

        queue_name = auth_inbound

        async with connection:
            channel = await connection.channel()

            queue = await channel.declare_queue(
                queue_name, auto_delete=True
            )
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        json_request = json.loads(message.body)
                        response = None

                        if json_request["task"] == "signup":
                            response = await SignUp(json_request["data"]).make()

                        elif json_request["task"] == "login":
                            response = await LogIn(json_request["data"]).make()

                        await self.send_response(response)


if __name__ == '__main__':
    authorization = Authorization()

    loop = asyncio.get_event_loop()

    authorization.loop = loop

    authorization.loop.create_task(authorization.get_tasks())
    loop.run_forever()
