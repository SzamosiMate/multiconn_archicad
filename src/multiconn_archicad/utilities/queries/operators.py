"""Define each test family's readable operator identifiers."""

from enum import StrEnum


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
