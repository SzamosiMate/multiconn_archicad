import inspect
from typing import get_type_hints, is_typeddict
import pytest
from pydantic import BaseModel

import multiconn_archicad.models.tapir.types as tapir_model_types
import multiconn_archicad.models.tapir.commands as tapir_model_commands
import multiconn_archicad.dicts.tapir.types as tapir_dict_types
import multiconn_archicad.dicts.tapir.commands as tapir_dict_commands

MODEL_MODULES = [tapir_model_types, tapir_model_commands]
DICT_MODULES = [tapir_dict_types, tapir_dict_commands]


def _collect_pydantic_models():
    models = []
    for mod in MODEL_MODULES:
        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if issubclass(cls, BaseModel) and cls.__module__ == mod.__name__:
                models.append((f"{mod.__name__.split('.')[-1]}.{name}", cls))
    return models


def _collect_typed_dicts():
    dicts = []
    for mod in DICT_MODULES:
        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if is_typeddict(cls) and cls.__module__ == mod.__name__:
                dicts.append((f"{mod.__name__.split('.')[-1]}.{name}", cls))
    return dicts


PYDANTIC_MODELS = _collect_pydantic_models()
TYPED_DICTS = _collect_typed_dicts()


@pytest.mark.parametrize("name,model_cls", PYDANTIC_MODELS, ids=[m[0] for m in PYDANTIC_MODELS])
def test_pydantic_model_completeness(name: str, model_cls: type[BaseModel]):
    """
    Verifies that every generated Pydantic model is fully defined at import time.
    Fails immediately if forward references are unresolved or missing model_rebuild().
    """
    assert model_cls.__pydantic_complete__ is True, (
        f"Model '{name}' was not completed at module load time! "
        f"A dependency is defined after it, or it is missing a '.model_rebuild()' call."
    )

    # Calling model_json_schema() forces resolution of all field annotations
    # and will raise PydanticUserError if incomplete.
    try:
        model_cls.model_json_schema()
    except Exception as e:
        pytest.fail(f"Failed building schema for Pydantic model '{name}': {e}")


@pytest.mark.parametrize("name,dict_cls", TYPED_DICTS, ids=[d[0] for d in TYPED_DICTS])
def test_typed_dict_annotations_resolve(name: str, dict_cls: type):
    """
    Verifies that every TypedDict's annotations can be evaluated at runtime
    without encountering NameErrors from unresolved forward references.
    """
    try:
        hints = get_type_hints(dict_cls)
        assert hints is not None
    except Exception as e:
        pytest.fail(f"Failed evaluating runtime annotations for TypedDict '{name}': {e}")