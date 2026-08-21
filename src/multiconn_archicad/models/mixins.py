from typing import Any
from pydantic import BaseModel, ConfigDict, model_validator, ValidationInfo

_MODEL_KEYS_CACHE: dict[type, set[str]] = {}

class StrictValidationMixin(BaseModel):
    """
    Enforces strict validation by rejecting unknown keys that can be turned off using validation context.
    Designed for MCP Servers / LLM inputs.
    """

    @model_validator(mode="before")
    @classmethod
    def forbid_extras_unless_api(cls, data: Any, info: ValidationInfo):
        if info.context and info.context.get("ignore_extra_keys"):
            return data
        if cls.model_config.get("extra") == "allow":
            return data

        if isinstance(data, dict):
            allowed_keys = _MODEL_KEYS_CACHE.get(cls)
            if allowed_keys is None:
                allowed_keys = set(cls.model_fields.keys())
                for field in cls.model_fields.values():
                    if field.alias:
                        allowed_keys.add(field.alias)
                _MODEL_KEYS_CACHE[cls] = allowed_keys

            extra_keys = data.keys() - allowed_keys
            if extra_keys:
                raise ValueError(
                    f"Extra fields not allowed in {cls.__name__}: {', '.join(extra_keys)}"
                )

        return data


class FrozenMixin(BaseModel):
    """
    Makes all models immutable and hashable.
    Useful for using models as dictionary keys, in sets, or for thread safety.
    """
    model_config = ConfigDict(frozen=True)


class StripWhitespaceMixin(BaseModel):
    """
    Automatically strips leading and trailing whitespace from all string fields.
    Extremely useful for cleaning up human-entered BIM data.
    """

    @model_validator(mode="before")
    @classmethod
    def strip_strings(cls, data: Any):
        if isinstance(data, dict):
            data = dict(data)
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = value.strip()
        return data


class OmitDefaultsMixin(BaseModel):
    """
    Overrides dumping so that fields with default values are NOT included in the JSON payload.
    Highly useful for minimizing HTTP payload sizes.
    """

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_defaults", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        kwargs.setdefault("exclude_defaults", True)
        return super().model_dump_json(**kwargs)