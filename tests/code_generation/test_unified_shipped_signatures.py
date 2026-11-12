import ast
from collections.abc import Sequence
from importlib import import_module
from typing import get_type_hints
from unittest.mock import MagicMock
from uuid import UUID

from multiconn_archicad.clients.unified_api.tapir.property import PropertyCommands
from multiconn_archicad.clients.unified_api.tapir.project import ProjectCommands
from multiconn_archicad.models.tapir.types import (
    ElementId,
    ElementIdArrayItem,
    ElementPropertyValue,
    ElementPropertyValueInput,
    PropertyId,
    PropertyValue,
)
from code_generation.unified.api_generator.shipped_signatures import extract_signatures, load_shipped_signatures


def test_shipped_signature_extractor_records_keyword_only_arguments():
    source = """
class ProjectCommands:
    def save_as_module_file(self, path, elements=None, *, overwrite=None) -> None:
        return self._core.post_tapir_command("SaveAsModuleFile", {})

    def save_as_module_file_dry_run(self, path) -> str:
        return self._core.post_tapir_command("SaveAsModuleFile", {})
"""
    assert extract_signatures(source, "post_tapir_command") == {
        "SaveAsModuleFile": {
            "save_as_module_file": {"parameters": ["path", "elements", "*", "overwrite"], "returns": "None"},
            "save_as_module_file_dry_run": {"parameters": ["path"], "returns": "str"},
        }
    }


def test_generator_preserves_shipped_order_and_keyword_only_arguments():
    generator = import_module("code_generation.unified.api_generator.02_generate_method_code")
    command = {"name": "SaveAsModuleFile", "source": "tapir", "description": "Save a module."}
    baseline = load_shipped_signatures()["tapir"][command["name"]]["save_as_module_file"]
    for params in (baseline["parameters"], [*baseline["parameters"], "*", "overwrite"]):
        shipped = {"save_as_module_file": {**baseline, "parameters": params}}
        generated = generator.generate_method_code(command, shipped)
        signature = ast.parse(generated["method_code"]).body[0].args
        assert [arg.arg for arg in signature.args] == ["self", "module_file_path", "elements"]
        assert [arg.arg for arg in signature.kwonlyargs] == ["overwrite"]


def test_legacy_module_file_positional_call_binds_elements():
    core = MagicMock()
    core.post_tapir_command.return_value = {"success": True}
    guid = UUID(int=1)
    elements = [ElementIdArrayItem(elementId=ElementId(guid=guid))]
    ProjectCommands(core).save_as_module_file("module.mod", elements, overwrite=False)
    core.post_tapir_command.assert_called_once_with(
        "SaveAsModuleFile",
        {"moduleFilePath": "module.mod", "elements": [{"elementId": {"guid": str(guid)}}], "overwrite": False},
    )


def test_element_property_value_remains_constructible():
    core = MagicMock()
    core.post_tapir_command.return_value = {"executionResults": [{"success": True}]}
    guid = UUID(int=1)
    value = ElementPropertyValue(
        elementId=ElementId(guid=guid), propertyId=PropertyId(guid=guid), propertyValue=PropertyValue(value="12")
    )
    commands = PropertyCommands(core)
    payload = {"elementPropertyValues": [value.model_dump(mode="json")]}
    result = commands.set_property_values_of_elements([value])
    assert result[0].success
    core.post_tapir_command.assert_called_once_with("SetPropertyValuesOfElements", payload)
    assert (
        get_type_hints(PropertyCommands.set_property_values_of_elements)["element_property_values"]
        == Sequence[ElementPropertyValueInput]
    )

    core.post_tapir_command.reset_mock()
    core.post_tapir_command.return_value = {
        "dryRun": True,
        "executionResults": [{"success": True, "wouldChange": {"oldValue": "5", "newValue": "12"}}],
    }
    preview = commands.set_property_values_of_elements_dry_run([value])
    assert preview.dryRun
    assert preview.executionResults[0].wouldChange.newValue == "12"
    core.post_tapir_command.assert_called_once_with("SetPropertyValuesOfElements", {**payload, "dryRun": True})
