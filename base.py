from decimal import Decimal, InvalidOperation
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, ValidationInfo, field_validator


class FormattedSchema(BaseModel):
    @classmethod
    def _field_accepts_string(cls, field_name: str) -> bool:
        field = cls.model_fields.get(field_name)
        if field is None:
            return False

        annotation = field.annotation
        if annotation is str:
            return True

        origin = get_origin(annotation)
        if origin in {Union, getattr(__import__("types"), "UnionType", Union)}:
            return str in get_args(annotation)

        return False

    @staticmethod
    def _format_numeric_string(value: str) -> str:
        text = value.strip()
        if not text or text.lower() == "null":
            return value

        try:
            number = Decimal(text)
        except InvalidOperation:
            return value

        if not number.is_finite():
            return value

        return f"{number:.2f}"

    @field_validator("*", mode="before", check_fields=False)
    @classmethod
    def _normalize_numeric_strings(cls, value: Any, info: ValidationInfo):
        if not isinstance(value, str):
            return value
        if not cls._field_accepts_string(info.field_name):
            return value
        return cls._format_numeric_string(value)