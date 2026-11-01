"""Define each test family's readable operator identifiers."""

from enum import StrEnum


class ClassificationOperator(StrEnum):
    IS = "is"
    IS_NOT = "is not"
    HAS_VALUE = "has value"
    HAS_NO_VALUE = "has no value"
    IS_IN_BRANCH_OF = "is in branch of"
    IS_NOT_IN_BRANCH_OF = "is not in branch of"
    IS_DIRECT_CHILD_OF = "is direct child of"
    IS_NOT_DIRECT_CHILD_OF = "is not direct child of"

    @property
    def requires_value(self) -> bool:
        return self not in (self.HAS_VALUE, self.HAS_NO_VALUE)


class BooleanOperator(StrEnum):
    IS = "is"
    IS_NOT = "is not"


class TextOperator(StrEnum):
    IS = "is"
    IS_NOT = "is not"
    CONTAINS = "contains"
    DOES_NOT_CONTAIN = "does not contain"
    STARTS_WITH = "starts with"
    ENDS_WITH = "ends with"


class NumberOperator(StrEnum):
    IS = "is"
    IS_NOT = "is not"
    GREATER_THAN = "is greater than"
    GREATER_THAN_OR_EQUAL_TO = "is greater than or equal to"
    LESS_THAN = "is less than"
    LESS_THAN_OR_EQUAL_TO = "is less than or equal to"
