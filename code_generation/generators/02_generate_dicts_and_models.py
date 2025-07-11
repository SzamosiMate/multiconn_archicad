from datamodel_code_generator import DataModelType, InputFileType, generate, LiteralType
from paths import paths

generate(
    paths.MASTER_SCHEMA_OUTPUT,
    input_file_type=InputFileType.JsonSchema,
    output=paths.RAW_PYDANTIC_MODELS,
    output_model_type=DataModelType.PydanticV2BaseModel,
    enum_field_as_literal=LiteralType.One,
    use_union_operator=True,
    use_double_quotes=True,
    collapse_root_models=True
)

generate(
    paths.MASTER_SCHEMA_OUTPUT,
    input_file_type=InputFileType.JsonSchema,
    output=paths.RAW_TYPED_DICTS,
    output_model_type=DataModelType.TypingTypedDict,
    enum_field_as_literal=LiteralType.All,
    use_union_operator=True,
    use_double_quotes=True,
    collapse_root_models=False
)
