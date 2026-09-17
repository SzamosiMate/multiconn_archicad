from datamodel_code_generator import DataModelType, InputFileType, LiteralType, TargetPydanticVersion, generate
from datamodel_code_generator.format import Formatter

from code_generation.tapir.paths import tapir_paths

CUSTOM_BASE_CLASS = "multiconn_archicad.models.base.APIModel"


def main() -> None:
    print("Generating Pydantic models")
    generate(
        tapir_paths.MASTER_SCHEMA_OUTPUT,
        input_file_type=InputFileType.JsonSchema,
        schema_version="2019-09",
        output=tapir_paths.RAW_PYDANTIC_MODELS,
        output_model_type=DataModelType.PydanticV2BaseModel,
        target_pydantic_version=TargetPydanticVersion.V2,
        base_class=CUSTOM_BASE_CLASS,
        enum_field_as_literal=LiteralType.One,
        capitalise_enum_members=True,
        keep_model_order=False,
        use_union_operator=True,
        use_double_quotes=True,
        collapse_root_models=True,
        field_constraints=True,
        use_annotated=True,
        use_one_literal_as_default=True,
        use_schema_description=True,
        disable_timestamp=True,
        formatters=[Formatter.BLACK, Formatter.ISORT],
        skip_root_model=True,
    )

    print("Generating Typed Dicts")
    generate(
        tapir_paths.MASTER_SCHEMA_OUTPUT,
        input_file_type=InputFileType.JsonSchema,
        schema_version="2019-09",
        output=tapir_paths.RAW_TYPED_DICTS,
        output_model_type=DataModelType.TypingTypedDict,
        enum_field_as_literal=LiteralType.All,
        capitalise_enum_members=True,
        keep_model_order=False,
        use_union_operator=True,
        use_double_quotes=True,
        collapse_root_models=False,
        use_closed_typed_dict=False,
        use_schema_description=True,
        disable_timestamp=True,
        formatters=[Formatter.BLACK, Formatter.ISORT],
        skip_root_model=True,
    )

    print("Generation complete")


if __name__ == "__main__":
    main()
