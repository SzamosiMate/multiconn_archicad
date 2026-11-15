from typing import Any, Literal, get_origin
from pydantic import BaseModel, ConfigDict, model_serializer
from pydantic_core import PydanticUndefined
from .config import _Registry

_DEFAULT_CONFIG: dict[str, Any] = {
    "extra": "ignore",
    "populate_by_name": True,
    "serialize_by_alias": True,
    "allow_inf_nan": False,
}

_merged_config = dict(_DEFAULT_CONFIG)
for mixin in _Registry.mixins:
    if hasattr(mixin, "model_config"):
        _merged_config.update(mixin.model_config)

_bases = _Registry.mixins + (BaseModel,)


class APIModel(*_bases):
    """A custom base model for the Unified API"""

    model_config = ConfigDict(**_merged_config)

    @model_serializer(mode="wrap")
    def _preserve_defaulted_literals(self, handler: Any, info: Any) -> Any:
        data = handler(self)
        if not info.exclude_defaults or not isinstance(data, dict):
            return data

        by_alias = info.by_alias
        if by_alias is None:
            by_alias = type(self).model_config.get("serialize_by_alias", False)
        candidates = set()
        for name, field in type(self).model_fields.items():
            if (
                get_origin(field.annotation) is not Literal
                or field.default is PydanticUndefined
                or field.default_factory is not None
            ):
                continue
            key = (field.serialization_alias or field.alias or name) if by_alias else name
            if key not in data and (info.include is None or name in info.include):
                candidates.add(name)
        if candidates:
            # Re-enter with default exclusion disabled, preserving the caller's filters
            # and field serializers. The constrained pass never traverses nested models.
            restored = self.model_dump(
                mode=info.mode,
                by_alias=by_alias,
                include=candidates,
                exclude=info.exclude,
                exclude_unset=info.exclude_unset,
                exclude_defaults=False,
                exclude_none=info.exclude_none,
                context=info.context,
            )
            for key, value in restored.items():
                data.setdefault(key, value)
        return data

    def model_dump(
        self,
        *,
        by_alias: bool = True,
        exclude_none: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return super().model_dump(
            by_alias=by_alias,
            exclude_none=exclude_none,
            **kwargs,
        )

    def model_dump_json(
        self,
        *,
        by_alias: bool = True,
        exclude_none: bool = True,
        **kwargs: Any,
    ) -> str:
        return super().model_dump_json(
            by_alias=by_alias,
            exclude_none=exclude_none,
            **kwargs,
        )


# =====================================================================
# LOCK CONFIGURATION
# =====================================================================
_Registry.locked = True
