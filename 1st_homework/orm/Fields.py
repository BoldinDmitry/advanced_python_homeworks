import abc
import hashlib
import binascii
import os

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
    @abc.abstractmethod
    def to_sql(value) -> str:
        pass


class IntField(Field):
    def __init__(self, required=True, default=None, pk=False):
        super().__init__(int, required, default, pk)

    @staticmethod
    def to_sql(value):
        return str(value)


class FloatField(Field):
    def __init__(self, required=True, default=None, pk=False):
        super().__init__(float, required, default, pk)

    @staticmethod
    def to_sql(value):
        return str(value)


class StringField(Field):
    def __init__(self, required=True, default=None, pk=False):
        super().__init__(str, required, default, pk)

    @staticmethod
    def to_sql(value):
        return f"'{value}'"


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

    @staticmethod
    def to_sql(value):
        return str(int(value))
