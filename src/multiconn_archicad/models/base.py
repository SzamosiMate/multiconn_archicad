from pydantic import BaseModel, ConfigDict

class APIModel(BaseModel):
    """A custom base model that forbids extra (unexpected) fields by default."""
    model_config = ConfigDict(
        extra="forbid",
    )