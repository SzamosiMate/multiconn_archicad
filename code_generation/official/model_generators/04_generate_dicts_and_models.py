from datamodel_code_generator import DataModelType, InputFileType, generate, LiteralType, TargetPydanticVersion
from datamodel_code_generator.format import Formatter
from code_generation.official.paths import official_paths

CUSTOM_BASE_CLASS = "multiconn_archicad.models.base.APIModel"

print("Generating Pydantic models")
generate(
    official_paths.MASTER_SCHEMA_OUTPUT,
    input_file_type=InputFileType.JsonSchema,
    schema_version="2019-09",
    output=official_paths.RAW_PYDANTIC_MODELS,
    output_model_type=DataModelType.PydanticV2BaseModel,
    target_pydantic_version=TargetPydanticVersion.V2,
    base_class=CUSTOM_BASE_CLASS,
    enum_field_as_literal=LiteralType.One,
    use_union_operator=True,
    use_double_quotes=True,
    collapse_root_models=True,
    field_constraints=True,
    use_annotated=True,
    use_one_literal_as_default=True,
    use_schema_description=True,
    formatters=[Formatter.BLACK, Formatter.ISORT],
    skip_root_model=True,
)

print("Generating Typed Dicts")
generate(
    official_paths.MASTER_SCHEMA_OUTPUT,
    input_file_type=InputFileType.JsonSchema,
    schema_version="2019-09",
    output=official_paths.RAW_TYPED_DICTS,
    output_model_type=DataModelType.TypingTypedDict,
    enum_field_as_literal=LiteralType.All,
    use_union_operator=True,
    use_double_quotes=True,
    collapse_root_models=False,
    use_closed_typed_dict=False,
    use_schema_description=True,
    formatters=[Formatter.BLACK, Formatter.ISORT],
    skip_root_model=True,
)

print("generation complete")