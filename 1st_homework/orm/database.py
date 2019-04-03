from orm.models import Model
from orm import Fields


class User(Model):
    username = Fields.StringField()
    password = Fields.PasswordField()
    is_registered = Fields.BoolField()

    def __str__(self):
        return self.username

    class Meta:
        table_name = "Users"


User.objects.filter(username="test").update(username="abc")
print(User.objects.filter(username="abc").get())
