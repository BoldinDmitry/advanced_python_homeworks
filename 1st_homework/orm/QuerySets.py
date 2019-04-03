import abc
from .database import conn, cursor

class QuerySet:
    def __init__(self, model_cls):
        self.model_cls = model_cls

    @abc.abstractmethod
    def build(self):
        pass


class QuerySetWhere(QuerySet):
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
            field = self.model_cls._fields.get(name, "id")
            if field == "id":
                self.where[name] = value
            else:
                self.where[name] = field.to_sql(value)

    def build(self):
        """
        filter(name__gt=1).filter(title=5)
        :return:
        """
        names, values = [], []
        for name_param, value in self.where.items():
            name_splited = name_param.split("__")
            if len(name_splited) == 2:
                names += [f"{name_splited[0]} {self.params_to_sql[name_splited[1]]} ?"]
            else:
                names += [f"{name_splited[0]} = ?"]
            values += [value]

        names = " AND ".join(names)
        if len(names) > 0:
            return "WHERE " + names, values
        else:
            return "", None


class UpdateQuerySet(QuerySet, abc.ABC):
    def __init__(self, model_cls, **kwargs):
        super().__init__(model_cls)

    @abc.abstractmethod
    def update(self, **kwargs):
        pass


class SelectQuerySet(QuerySetWhere, UpdateQuerySet):
    def __init__(self, model_cls, **kwargs):
        super().__init__(model_cls)
        self.fields = None
        self.filter(**kwargs)

    def get(self, *args):
        args = "*" if args == () else args
        q = ["SELECT"]
        q += [arg for arg in args]
        q += [f"FROM {self.model_cls.Meta.table_name}"]
        names, values = self.build()
        q += [names]
        sqlite_command = " ".join(q)
        cursor.execute(sqlite_command, values)
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

    def update(self, **kwargs):
        objects = self.get("*")
        for object in objects:
            for kwarg in kwargs.items():
                name = kwarg[0]
                value = kwarg[1]
                if name in object._fields:
                    setattr(object, name, value)
                object.update()

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
