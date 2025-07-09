from datamodel_code_generator import DataModelType, InputFileType, generate, LiteralType
import pathlib

base_input_file = pathlib.Path("../schema/tapir_master_schema.json")
base_output = pathlib.Path("../temp_models/input_base_models.py")
dict_output = pathlib.Path("../temp_models/input_typed_dicts.py")


generate(
    base_input_file,
    input_file_type=InputFileType.JsonSchema,
    output=base_output,
    output_model_type=DataModelType.PydanticV2BaseModel,
    enum_field_as_literal=LiteralType.All,
    use_union_operator=True,
    use_double_quotes=True,
    collapse_root_models=True
)

generate(
    base_input_file,
    input_file_type=InputFileType.JsonSchema,
    output=dict_output,
    output_model_type=DataModelType.TypingTypedDict,
    enum_field_as_literal=LiteralType.All,
    use_union_operator=True,
    use_double_quotes=True,
    collapse_root_models=True
)
