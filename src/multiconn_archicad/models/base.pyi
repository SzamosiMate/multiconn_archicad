from typing import Any

from pydantic import BaseModel

# Runtime bases include configured mixins. Expose their stable BaseModel
# interface without making every generated model inherit an unknown/Any base.
class APIModel(BaseModel):
    def model_dump(
        self, *, by_alias: bool | None = True, exclude_none: bool = True, **kwargs: Any
    ) -> dict[str, Any]: ...
    def model_dump_json(self, *, by_alias: bool | None = True, exclude_none: bool = True, **kwargs: Any) -> str: ...
