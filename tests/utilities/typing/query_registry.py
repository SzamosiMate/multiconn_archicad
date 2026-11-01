"""Static regression checks; run mypy with --warn-unused-ignores, not Python.

The ignored calls must produce arg-type errors. An unused-ignore error therefore
detects a regression that would let unrelated types into the factory annotation.
Runtime-only union-shape and abstract-class checks live in the unit tests.
"""

from typing import Annotated, TypeAlias, Union

from pydantic import Field

from multiconn_archicad.utilities.queries import NumberTest, PropertyTest, TestRegistry, TextTest

AnnotatedTests: TypeAlias = Annotated[TextTest | NumberTest, Field(discriminator="kind")]
InvalidTests: TypeAlias = Annotated[TextTest | str, Field(discriminator="kind")]

TestRegistry.from_union(PropertyTest)
TestRegistry.from_union(TextTest | NumberTest)
TestRegistry.from_union(Union[TextTest, NumberTest])
TestRegistry.from_union(AnnotatedTests)

TestRegistry.from_union(TextTest | str)  # type: ignore[arg-type]
TestRegistry.from_union(InvalidTests)  # type: ignore[arg-type]
TestRegistry.from_union(tuple[TextTest, NumberTest])  # type: ignore[arg-type]
