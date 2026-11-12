import importlib
from typing import Annotated, TypeAlias
from uuid import UUID

import pytest
from pydantic import Field, TypeAdapter, ValidationError

cleaner = importlib.import_module("code_generation.tapir.model_generators.03_model_cleaner")
pytestmark = pytest.mark.unit


@pytest.mark.parametrize("annotated", [False, True])
@pytest.mark.parametrize("nullable", [False, True])
@pytest.mark.parametrize(
    "arguments",
    [
        'pattern="uuid"',
        'pattern="uuid", description="Azonosító"',
        'description="Azonosító", pattern="uuid"',
        'description="Azonosító", pattern="uuid", title="Identifier"',
        '\n        description="Azonosító",\n        pattern="uuid",\n    ',
    ],
)
def test_uuid_pattern_removal_preserves_descriptions_and_string_constraints(annotated, nullable, arguments):
    annotation = "UUID | None" if nullable else "UUID"
    declaration = (
        f"guid: Annotated[{annotation}, Field({arguments})]"
        if annotated
        else f"guid: {annotation} = Field({arguments})"
    )
    source = f"""from typing import Annotated
from uuid import UUID
from pydantic import BaseModel, Field

class Example(BaseModel):
    {declaration}
    date: str = Field(pattern=r"^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$")
"""
    cleaned = cleaner.remove_guid_pattern(source)
    namespace = {}
    exec(cleaned, namespace)
    model = namespace["Example"]
    model.model_rebuild(_types_namespace=namespace)
    identifier = "12345678-1234-1234-1234-123456789abc"
    instance = model(guid=identifier, date="2026-10-15")
    assert instance.guid == UUID(identifier)
    if nullable:
        assert model(guid=None, date="2026-10-15").guid is None
    if "description" in arguments:
        assert model.model_fields["guid"].description == "Azonosító"
    with pytest.raises(ValidationError):
        model(guid=identifier, date="invalid")
    with pytest.raises(ValidationError):
        model(guid="invalid", date="2026-10-15")
    assert cleaner.remove_guid_pattern(cleaned) == cleaned


def test_uuid_without_pattern_does_not_remove_a_later_string_pattern():
    source = """class Example:
    guid: Annotated[UUID, Field(description="Identifier")]
    date: Annotated[str, Field(pattern="date", description="Date")]
"""
    assert cleaner.remove_guid_pattern(source) == source


def test_uuid_alias_pattern_is_removed_without_weakening_string_alias():
    source = """Identifier: TypeAlias = Annotated[UUID, Field(pattern="uuid", description="Identifier")]
Date: TypeAlias = Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]
"""
    cleaned = cleaner.remove_guid_pattern(source)
    namespace = {"UUID": UUID, "Annotated": Annotated, "Field": Field, "TypeAlias": TypeAlias}
    exec(cleaned, namespace)
    identifier = "12345678-1234-1234-1234-123456789abc"
    assert TypeAdapter(namespace["Identifier"]).validate_python(identifier) == UUID(identifier)
    with pytest.raises(ValidationError):
        TypeAdapter(namespace["Identifier"]).validate_python("invalid")
    with pytest.raises(ValidationError):
        TypeAdapter(namespace["Date"]).validate_python("invalid")
