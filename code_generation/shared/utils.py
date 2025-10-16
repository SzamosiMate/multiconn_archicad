import re


def camel_to_snake(name: str) -> str:
    """
    Converts a camelCase or PascalCase string to snake_case, correctly
    handling acronyms and numbers (e.g., '3D', 'GDL', 'XML').
    """
    # 1) Insert underscore between a letter and a following digit:
    #    "Get3D" -> "Get_3D"
    name = re.sub(r'(?<=[A-Za-z])(?=\d)', '_', name)

    # 2) Insert underscore between an uppercase/digit and an Uppercase+lowercase sequence:
    #    handles "3DBounding" -> "3D_Bounding" and "XMLParser" -> "XML_Parser"
    name = re.sub(r'([A-Z0-9])([A-Z][a-z])', r'\1_\2', name)

    # 3) Insert underscore between a lowercase and uppercase letter:
    #    "getXML" -> "get_XML"
    name = re.sub(r'(?<=[a-z])([A-Z])', r'_\1', name)

    return name.lower()

if __name__ == "__main__":
    print(camel_to_snake("Get3DBoundingBoxes"))
    print(camel_to_snake("getXMLParserID"))
    print(camel_to_snake("Export2DViews"))
    print(camel_to_snake("Parse3DMData"))
    print(camel_to_snake("OpenGDLFile"))
