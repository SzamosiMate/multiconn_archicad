import re


def camel_to_snake(name: str) -> str:
    """
    Converts a camelCase or PascalCase string to snake_case, correctly
    handling acronyms and numbers (e.g., '3D', 'GDL').
    """
    # Handles cases like 'Get3DBoundingBoxes' -> 'Get_3D_BoundingBoxes'
    name = re.sub(r"([A-Za-z])(\d+)", r"\1_\2", name)
    name = re.sub(r"(\d+)([A-Za-z])", r"\1_\2", name)

    # Handles standard camelCase and initialisms like 'GDL'
    name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)

    return name.lower()
