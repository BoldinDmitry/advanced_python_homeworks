import binascii
import hashlib
import os
import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

types_convert = {
    int: "integer",
    float: "real",
    str: "text",
    bool: "boolean"

}


class Field:
    def __init__(self, f_type, required=True, default=None, pk=False):
        self.f_type = f_type
        self.required = required
        self.default = default

    def validate(self, value):
        if value is None and not self.required:
            return None
        elif self.required and value is None and self.default is None:
            raise ValueError('Required field is none and no default')
        elif self.required and value is None and self.default is not None:
            value = self.default
        return self.f_type(value)


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
        salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
        pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                      salt, 100000)
        pwdhash = binascii.hexlify(pwdhash)
        return (salt + pwdhash).decode('ascii')

    @staticmethod
    def verify_password(stored_password, provided_password):
        """Verify a stored password against one provided by user"""
        salt = stored_password[:64]
        stored_password = stored_password[64:]
        pwdhash = hashlib.pbkdf2_hmac('sha512',
                                      provided_password.encode('utf-8'),
                                      salt.encode('ascii'),
                                      100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        return pwdhash == stored_password


class BoolField(Field):
    def __init__(self, required=True, default=None):
        super().__init__(bool, required, default)


class ModelMeta(type):
    def __new__(mcs, name, bases, namespace):
        if name == 'Model':
            return super().__new__(mcs, name, bases, namespace)

        meta = namespace.get('Meta')
        if meta is None:
            raise ValueError('Meta is None')
        if not hasattr(meta, 'table_name'):
            raise ValueError('table_name is empty')

        # todo mro

        fields = {k: v for k, v in namespace.items()
                  if isinstance(v, Field)}
        namespace['_fields'] = fields
        namespace['_table_name'] = meta.table_name

        return super().__new__(mcs, name, bases, namespace)


class Manage:
    def __init__(self):
        self.model_cls = None

    def __get__(self, instance, owner):
        if self.model_cls is None:
            self.model_cls = owner
        return self

    def create(self, **kwargs):
        return self.model_cls(**kwargs).save()

    def all(self):
        names_columns_cmd = f"PRAGMA table_info({self.model_cls.Meta.table_name})"
        names = [name[1] for name in cursor.execute(names_columns_cmd).fetchall()]

        all_rows_cmd = f"select * from {self.model_cls.Meta.table_name}"
        all_rows = cursor.execute(all_rows_cmd).fetchall()

        objects = []
        for row in all_rows:
            kwargs = dict(zip(names, row))
            model = self.model_cls(**kwargs)
            setattr(model, "id", row[0])
            objects.append(model)
        return objects

    def filter(self, **kwargs):
        names_columns_cmd = f"PRAGMA table_info({self.model_cls.Meta.table_name})"
        names = [name[1] for name in cursor.execute(names_columns_cmd).fetchall()]

        filter_cmd = f"""SELECT * FROM {self.model_cls.Meta.table_name} WHERE """
        conditions = ""

        for name, value in kwargs.items():
            if conditions != "":
                conditions += " AND "
            if type(value) is bool:
                conditions += f"{name} = {int(value)}"
            elif type(value) is str:
                conditions += f"{name} = '{value}'"
            else:
                conditions += f"{name} = {value}"

        filter_cmd += conditions

        all_rows = cursor.execute(filter_cmd).fetchall()

        objects = []
        for row in all_rows:
            kwargs = dict(zip(names, row))
            model = self.model_cls(**kwargs)
            setattr(model, "id", row[0])
            objects.append(model)
        return objects

    def get(self, **kwargs):
        model = self.filter(**kwargs)
        if len(model) > 1:
            raise ValueError("Too many objects found")
        if len(model) == 0:
            raise ValueError("No objects found")

        return model[0]


class Model(metaclass=ModelMeta):
    id = None

    class Meta:
        table_name = ''

    objects = Manage()
    # todo DoesNotExist
    # Бросать искоючение, если, например, get вернул не объект, а None
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
        create_command = f"""CREATE TABLE IF NOT EXISTS {meta.table_name} ({table_fields})"""
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
        table_name = 'Users'
