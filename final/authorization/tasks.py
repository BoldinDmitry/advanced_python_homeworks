import uuid
from abc import abstractmethod
from datetime import datetime, timedelta

from final.orm import fields
from final.orm.models import Model


class User(Model):
    email = fields.StringField()
    password = fields.StringField()
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


class Task:
    loop = None

    @abstractmethod
    def make(self):
        pass


class SignUp(Task):
    def __init__(self, req):
        self.name = req["name"]
        self.email = req["email"]
        self.password = req["password"]

    async def exists(self):
        users = await User.objects.filter(email=self.email, name=self.name).get()
        return users != []

    async def make(self):
        if await self.exists():
            return {
                "status": "error",
                "info": "user with given email and name already exists"
            }

        user = User(
            email=self.email,
            password=self.password,
            name=self.name,
            created_date=datetime.now(),
            last_login_date=datetime.now()
        )
        await user.save()
        return {"status": "ok"}


class LogIn(Task):
    def __init__(self, req):
        self.email = req["email"]
        self.password = req["password"]
        self.user = None

    async def exists(self):
        self.user = await User.objects.filter(email=self.email, password=self.password).get()

        if not self.user:
            return False

        return True

    async def make(self):
        if not await self.exists():
            return {
                "status": "error",
                "info": "user with given email and password not exists"
            }

        self.user = self.user[0]

        user_token = str(uuid.uuid4())
        expire_date = datetime.now() + timedelta(days=31)

        token = Token(token=user_token, expire_date=expire_date, user_id=self.user.id)

        await token.save()

        return {"token": user_token, "expire_date": expire_date.isoformat()}
