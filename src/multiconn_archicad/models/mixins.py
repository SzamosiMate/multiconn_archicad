from typing import Any
from pydantic import BaseModel, ConfigDict, model_validator, ValidationInfo

_MODEL_KEYS_CACHE: dict[type, set[str]] = {}

def _get_allowed_keys(cls: type[BaseModel]) -> set[str]:
    """Helper for context-based validation to extract and cache allowed field names and aliases."""
    allowed_keys = _MODEL_KEYS_CACHE.get(cls)
    if allowed_keys is None:
        allowed_keys = set(cls.model_fields.keys())
        for field in cls.model_fields.values():
            if field.alias:
                allowed_keys.add(field.alias)
        _MODEL_KEYS_CACHE[cls] = allowed_keys
    return allowed_keys


class ForbidExtrasMixin(BaseModel):
    """
    Enforces strict schema compliance by forbidding extra/unknown fields using native Pydantic config.
    Concrete models configured with extra='allow' (e.g. AddOnCommandParameters) will override this.
    """
    model_config = ConfigDict(extra="forbid")


class ContextualForbidExtrasMixin(BaseModel):
    """
    Forbids extra/unknown keys by default, but allows bypassing via validation context:
        model.model_validate(data, context={"ignore_extra_keys": True})

    Useful for strictly validating user/LLM inputs while optionally allowing loose API returns.
    """

    @model_validator(mode="before")
    @classmethod
    def forbid_extras_unless_context(cls, data: Any, info: ValidationInfo) -> Any:
        if info.context and info.context.get("ignore_extra_keys"):
            return data
        if cls.model_config.get("extra") == "allow":
            return data

        if isinstance(data, dict):
            allowed_keys = _get_allowed_keys(cls)
            extra_keys = data.keys() - allowed_keys
            if extra_keys:
                raise ValueError(
                    f"Extra fields not allowed in {cls.__name__}: {', '.join(sorted(extra_keys))}"
                )

        return data


class StrictMixin(BaseModel):
    """
    Enforces strict Pydantic type validation (`strict=True`).
    Disallows type coercions (e.g. "123" -> 123, 1.0 -> 1, "true" -> True).
    """
    model_config = ConfigDict(strict=True)


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