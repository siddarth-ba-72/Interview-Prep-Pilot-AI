from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """camelCase on the wire and in Mongo; snake_case in Python. Null fields are kept in API output."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        protected_namespaces=(),
        use_enum_values=True,
    )
