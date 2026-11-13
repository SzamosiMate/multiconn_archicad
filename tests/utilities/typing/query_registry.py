"""Static regression checks; run mypy with --warn-unused-ignores, not Python.

The ignored calls must produce arg-type errors. An unused-ignore error therefore
detects a regression that would let unrelated types into the factory annotation.
Runtime-only union-shape and abstract-class checks live in the unit tests.
"""

from typing import Annotated, TypeAlias, Union

from pydantic import Field

from multiconn_archicad.utilities.queries import IntegerTest, RealTest, PropertyTest, TestRegistry, TextTest

AnnotatedTests: TypeAlias = Annotated[TextTest | IntegerTest | RealTest, Field(discriminator="kind")]
InvalidTests: TypeAlias = Annotated[TextTest | str, Field(discriminator="kind")]

TestRegistry.from_union(PropertyTest)
TestRegistry.from_union(TextTest | IntegerTest | RealTest)
TestRegistry.from_union(Union[TextTest, IntegerTest, RealTest])
TestRegistry.from_union(AnnotatedTests)

TestRegistry.from_union(TextTest | str)  # type: ignore[arg-type]
TestRegistry.from_union(InvalidTests)  # type: ignore[arg-type]
TestRegistry.from_union(tuple[TextTest, RealTest])  # type: ignore[arg-type]
