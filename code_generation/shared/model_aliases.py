"""Python compatibility names emitted by both Tapir model splitters."""

TAPIR_TYPE_ALIASES = {
    "PropertyExpressionUpdate": "PropertyDefinitionUpdate",
}


def render_type_aliases(aliases: dict[str, str], definition_names: set[str]) -> str:
    """Render direct aliases after their targets, rejecting stale or conflicting names."""
    declarations = []
    for alias, target in sorted(aliases.items()):
        if alias in definition_names:
            raise ValueError(f"Compatibility alias '{alias}' conflicts with a generated definition.")
        if target not in definition_names:
            raise ValueError(f"Compatibility alias '{alias}' targets missing definition '{target}'.")
        declarations.append(f"{alias}: TypeAlias = {target}")
    return "\n\n\n".join(declarations)
