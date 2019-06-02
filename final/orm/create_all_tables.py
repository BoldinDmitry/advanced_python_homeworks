import asyncio

import aiosqlite

from final.orm import fields
from final.orm.models import Model
from final.orm.query_sets import QuerySet


class User(Model):
    email = fields.StringField()
    password = fields.PasswordField()
    name = fields.StringField()
    created_date = fields.DateTimeField()
    last_login_date = fields.DateTimeField()

    def __str__(self):
        return self.name

    class Meta:
        table_name = "Users"


class Token(Model):
    token = fields.StringField()
    user_id = fields.IntField()
    expire_date = fields.DateTimeField()

    class Meta:
        table_name = "Tokens"


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


async def make_connection(loop):
    QuerySet.loop = loop
    QuerySet.conn = await aiosqlite.connect("database.db", loop=loop)

    Model.loop = loop
    Model.conn = await aiosqlite.connect("database.db", loop=loop)

    await CrawlerStats.create_table(CrawlerStats)
    await User.create_table(User)
    await Token.create_table(Token)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    a = asyncio.ensure_future(make_connection(loop))
    loop.run_until_complete(a)
