from typing import Any
from pydantic import BaseModel, ConfigDict

class APIModel(BaseModel):
    """A custom base model for the Unified API"""
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )

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