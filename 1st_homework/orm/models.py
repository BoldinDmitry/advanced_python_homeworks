from .Fields import Field
from .QuerySets import Manage
from .database import conn, cursor

types_convert = {int: "integer", float: "real", str: "text", bool: "boolean"}


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
        names = []
        values = []
        for name, value in self.__dict__.items():
            names += [name]
            values += [self._fields[name].to_sql(value)]

        names = ",".join(names)
        values = ",".join(values)
        insert_command = f"""INSERT INTO {self.Meta.table_name} ({names}) VALUES ({values});"""
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
        values = []
        names = []
        for name, value in self.__dict__.items():

            if name != "id":
                values += [self._fields[name].to_sql(value)]
                names += [f"{name} = ?"]

        names = ", ".join(names)
        update_cmd = f"UPDATE {self.Meta.table_name} SET {names} WHERE ID = {int(self.id)};"
        conn.execute(update_cmd, values)
        conn.commit()
