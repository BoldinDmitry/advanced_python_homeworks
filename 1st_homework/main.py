import abc
import binascii
import hashlib
import os
import sqlite3
import inspect
from abc import ABC

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

types_convert = {int: "integer", float: "real", str: "text", bool: "boolean"}


class Field:
    def __init__(self, f_type, required=True, default=None, pk=False):
        self.f_type = f_type
        self.required = required
        self.default = default

    def validate(self, value):
        if value is None and not self.required:
            return None
        elif self.required and value is None and self.default is None:
            raise ValueError("Required field is none and no default")
        elif self.required and value is None and self.default is not None:
            value = self.default
        return self.f_type(value)

    @staticmethod
    def to_sql(value) -> str:
        if type(value) is bool:
            return str(int(value))
        elif type(value) is str:
            return f"'{value}'"
        elif type(value) is float or type(value) is int:
            return value
        raise ValueError(f"{type(value)} is not supported")


class IntField(Field):
    def __init__(self, required=True, default=None, pk=False):
        super().__init__(int, required, default, pk)


class FloatField(Field):
    def __init__(self, required=True, default=None, pk=False):
        super().__init__(float, required, default, pk)


class StringField(Field):
    def __init__(self, required=True, default=None, pk=False):
        super().__init__(str, required, default, pk)


class PasswordField(StringField):
    def __init__(self, pk=False):
        super().__init__(pk=pk)

    def validate(self, value):
        value = super().validate(value)
        return self.hash_password(value)

    @staticmethod
    def hash_password(password):
        """Hash a password for storing."""
        salt = hashlib.sha256(os.urandom(60)).hexdigest().encode("ascii")
        pwdhash = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, 100000)
        pwdhash = binascii.hexlify(pwdhash)
        return (salt + pwdhash).decode("ascii")

    @staticmethod
    def verify_password(stored_password, provided_password):
        """Verify a stored password against one provided by user"""
        salt = stored_password[:64]
        stored_password = stored_password[64:]
        pwdhash = hashlib.pbkdf2_hmac(
            "sha512", provided_password.encode("utf-8"), salt.encode("ascii"), 100000
        )
        pwdhash = binascii.hexlify(pwdhash).decode("ascii")
        return pwdhash == stored_password


class BoolField(Field):
    def __init__(self, required=True, default=None):
        super().__init__(bool, required, default)


class ModelMeta(type):
    def __new__(mcs, name, bases, namespace):
        if name == "Model":
            return super().__new__(mcs, name, bases, namespace)

        meta = namespace.get("Meta")
        if meta is None:
            raise ValueError("Meta is None")
        if not hasattr(meta, "table_name"):
            raise ValueError("table_name is empty")

        for base in bases:
            namespace.update(base.__dict__.get("_fields", {}))

        fields = {k: v for k, v in namespace.items() if isinstance(v, Field)}
        namespace["_fields"] = fields
        namespace["_table_name"] = meta.table_name

        return super().__new__(mcs, name, bases, namespace)


class QuerySet:
    def __init__(self, model_cls):
        self.model_cls = model_cls

    @abc.abstractmethod
    def build(self):
        pass


class QuerySetWhere(QuerySet, ABC):
    params_to_sql = {"eq": "=", "bg": ">", "un": "<", None: "="}

    def __init__(self, model_cls):
        super().__init__(model_cls)
        self.where = {}

    def filter(self, **kwargs):
        """
        Сделать, чтобы можно было добавлять условия через __
        eq - равенство
        bg - больше
        un - меньше
        :param kwargs:
        :return:
        """
        for name, value in kwargs.items():
            if (
                name.split("__")[0] not in self.model_cls.__dict__
                and name.split("__")[0] != "id"
            ):
                raise ValueError(
                    f"No field {name} in {type(self.model_cls).__name__} found"
                )
            self.where[name] = Field.to_sql(value)

    def build_filter(self):
        """
        filter(name__gt=1).filter(title=5)
        :return:
        """
        sql_filter = ""
        for name_param, value in self.where.items():
            name_splited = name_param.split("__")
            if len(sql_filter) > 0:
                sql_filter += " AND "
            if len(name_splited) == 2:
                sql_filter += (
                    f"{name_splited[0]} {self.params_to_sql[name_splited[1]]} {value}"
                )
            else:
                sql_filter += f"{name_splited[0]} {self.params_to_sql[None]} {value}"
        if len(sql_filter) > 0:
            return "WHERE " + sql_filter
        else:
            return ""


class SelectQuerySet(QuerySetWhere, ABC):
    def __init__(self, model_cls, **kwargs):
        super().__init__(model_cls)
        self.fields = None
        self.filter(**kwargs)

    def get(self, *args):
        args = "*" if args == () else args
        q = ["SELECT"]
        q += [arg for arg in args]
        q += [f"FROM {self.model_cls.Meta.table_name}"]
        q += [self.build_filter()]
        sqlite_command = " ".join(q)

        cursor.execute(sqlite_command)
        rows = cursor.fetchall()
        var_names = self.model_cls._fields.keys()
        models = []
        for row in rows:
            kwargs = {}
            for name, value in zip(var_names, row[1:]):
                kwargs[name] = value
            model = self.model_cls(**kwargs)
            model.id = row[0]
            models.append(model)

        return models

    def filter(self, **kwargs):
        super().filter(**kwargs)
        return self


class Manage:
    def __init__(self):
        self.model_cls = None

    def __get__(self, instance, owner):
        if self.model_cls is None:
            self.model_cls = owner
        return self

    def all(self):
        return SelectQuerySet(self.model_cls)

    def filter(self, **kwargs):
        return SelectQuerySet(self.model_cls, **kwargs)


class Model(metaclass=ModelMeta):
    id = None

    class Meta:
        table_name = ""

    objects = Manage()

    if objects is None:
        raise ValueError("Objects manager is None")

    def __init__(self, *_, **kwargs):

        for field_name, field in self._fields.items():
            value = field.validate(kwargs.get(field_name))
            setattr(self, field_name, value)

    def save(self):
        names = ""
        values = ""
        for name, value in self.__dict__.items():
            names += name + ", "
            if type(value) is str:
                values += f"'{value}', "
            elif type(value) is bool:
                values += str(int(value)) + ", "
            else:
                values += str(value) + ", "

        insert_command = f"""INSERT INTO {self.Meta.table_name} ({names[:-2]}) VALUES ({values[:-2]});"""
        cursor.execute(insert_command)
        setattr(self, "id", cursor.lastrowid)
        conn.commit()

    def create_table(self):
        # Create table
        table_fields = "id INTEGER PRIMARY KEY AUTOINCREMENT"
        for field_name, field in self._fields.items():
            table_fields += ", " + field_name + " " + types_convert[field.f_type]
        create_command = (
            f"""CREATE TABLE IF NOT EXISTS {meta.table_name} ({table_fields})"""
        )
        cursor.execute(create_command)
        conn.commit()

    def delete(self):
        deletion_cmd = f"DELETE FROM {self.Meta.table_name} WHERE ID = {self.id};"
        cursor.execute(deletion_cmd)
        conn.commit()
        del self

    def update(self):
        fields_for_update = ""
        for name, value in self.__dict__.items():
            if type(value) is bool:
                fields_for_update += f"{name} = {int(value)}, "
            elif type(value) is str:
                fields_for_update += f"{name} = '{value}', "
            else:
                fields_for_update += f"{name} = {value}, "

        update_cmd = f"UPDATE {self.Meta.table_name} SET {fields_for_update[:-2]} WHERE ID = {self.id};"
        cursor.execute(update_cmd)
        conn.commit()


class User(Model):
    username = StringField()
    password = PasswordField()
    is_registered = BoolField()

    def __str__(self):
        return self.username

    class Meta:
        table_name = "Users"


u = User.objects.filter(id=4).filter(username="abc").get()[-1]
print(u.id)
