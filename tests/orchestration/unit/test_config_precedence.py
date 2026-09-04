import pytest
from pydantic import BaseModel, ConfigDict, ValidationError


# =========================================================================
# TIER 1: Baseline Defaults (No Mixins Configured)
# =========================================================================

def test_tier_1_baseline_defaults_apply_when_no_mixins(clean_models):
    """
    Proves that without mixins:
    1. Baseline extra="ignore" silently drops unknown fields.
    2. Baseline populate_by_name=True and serialize_by_alias=True are active.
    """
    from multiconn_archicad.models.base import APIModel
    from multiconn_archicad.models.tapir.types import Coordinate2D

    # 1. Config inspect: baseline has extra='ignore' and populate_by_name=True
    assert APIModel.model_config.get("extra") == "ignore"
    assert APIModel.model_config.get("populate_by_name") is True
    assert APIModel.model_config.get("serialize_by_alias") is True

    # 2. Functional check: Extra keys are silently ignored (not raising errors)
    coord = Coordinate2D.model_validate({"x": 10.0, "y": 20.0, "extra_ignored_key": "xyz"})
    assert coord.x == 10.0
    assert coord.y == 20.0
    assert not hasattr(coord, "extra_ignored_key")


# =========================================================================
# TIER 2: Mixin Overrides Baseline Config
# =========================================================================

def test_tier_2_mixin_overrides_baseline_and_preserves_other_defaults(clean_models):
    """
    Proves that injecting ForbidExtrasMixin:
    1. Overrides baseline extra="ignore" -> extra="forbid".
    2. Preserves other non-conflicting baseline defaults (populate_by_name, serialize_by_alias).
    """
    from multiconn_archicad.models.config import configure
    from multiconn_archicad.models.mixins import ForbidExtrasMixin

    # Inject the mixin
    configure(ForbidExtrasMixin)

    from multiconn_archicad.models.base import APIModel
    from multiconn_archicad.models.tapir.types import Coordinate2D

    # 1. Config inspect: extra was overridden by mixin, baseline keys were preserved
    assert APIModel.model_config.get("extra") == "forbid"
    assert APIModel.model_config.get("populate_by_name") is True
    assert APIModel.model_config.get("serialize_by_alias") is True

    # 2. Functional check: Standard model now raises ValidationError on extra keys
    with pytest.raises(ValidationError) as exc_info:
        Coordinate2D.model_validate({"x": 1.0, "y": 2.0, "forbidden_extra": 123})

    # Ensure the error is specifically Pydantic's native 'extra_forbidden'
    errors = exc_info.value.errors()
    assert any(err["type"] == "extra_forbidden" for err in errors)


# =========================================================================
# TIER 3: Concrete Model Overrides Both Base and Mixin
# =========================================================================

def test_tier_3_concrete_model_overrides_mixin(clean_models):
    """
    Proves that a leaf model with an explicit ConfigDict (e.g. extra="allow"):
    1. Overrides the mixin's extra="forbid".
    2. Overrides the baseline's extra="ignore".
    """
    from multiconn_archicad.models.config import configure
    from multiconn_archicad.models.mixins import ForbidExtrasMixin

    configure(ForbidExtrasMixin)

    from multiconn_archicad.models.tapir.types import Coordinate2D
    from multiconn_archicad.models.official.types import AddOnCommandParameters
    from multiconn_archicad.models.base import APIModel

    # 1. Define a custom leaf model to test custom override behavior
    class CustomPermissiveModel(APIModel):
        model_config = ConfigDict(extra="allow")
        name: str

    # 2. Coordinate2D (no local override) inherits extra="forbid" from mixin
    with pytest.raises(ValidationError):
        Coordinate2D(x=1.0, y=2.0, extra_key="fails")

    # 3. CustomPermissiveModel explicitly declares extra="allow" -> overrides mixin
    custom = CustomPermissiveModel(name="test", arbitrary_dynamic_field=999)
    assert custom.name == "test"
    assert getattr(custom, "arbitrary_dynamic_field") == 999

    # 4. Built-in AddOnCommandParameters (which has extra="allow") also overrides mixin
    addon_params = AddOnCommandParameters.model_validate({
        "archicadCustomPayload": {"guid": "123-abc"},
        "speedMultiplier": 1.5,
    })
    dumped = addon_params.model_dump()
    assert dumped["archicadCustomPayload"] == {"guid": "123-abc"}
    assert dumped["speedMultiplier"] == 1.5


# =========================================================================
# COMPLETE HIERARCHY: Multi-Mixin Composition + Overrides
# =========================================================================

def test_full_precedence_hierarchy_with_multiple_mixins(clean_models):
    """
    Proves the full stack in action simultaneously:
    - Baseline: populate_by_name=True
    - Mixin 1 (ForbidExtrasMixin): extra="forbid"
    - Mixin 2 (FrozenMixin): frozen=True
    - Mixin 3 (StrictMixin): strict=True
    - Leaf Model: overrides extra="allow" and frozen=False
    """
    from multiconn_archicad.models.config import configure
    from multiconn_archicad.models.mixins import ForbidExtrasMixin, FrozenMixin, StrictMixin

    # Configure multiple mixins with different ConfigDict keys
    configure(ForbidExtrasMixin, FrozenMixin, StrictMixin)

    from multiconn_archicad.models.base import APIModel
    from multiconn_archicad.models.tapir.types import Coordinate2D

    # 1. Inspect APIModel merged config
    assert APIModel.model_config.get("populate_by_name") is True  # From Baseline
    assert APIModel.model_config.get("extra") == "forbid"         # From ForbidExtrasMixin
    assert APIModel.model_config.get("frozen") is True            # From FrozenMixin
    assert APIModel.model_config.get("strict") is True            # From StrictMixin

    # 2. Verify standard model obeys all mixins
    coord = Coordinate2D(x=1.0, y=2.0)

    # Obey StrictMixin (no type coercion like "1.0" -> 1.0)
    with pytest.raises(ValidationError):
        Coordinate2D.model_validate({"x": "1.0", "y": 2.0})

    # Obey ForbidExtrasMixin
    with pytest.raises(ValidationError):
        Coordinate2D.model_validate({"x": 1.0, "y": 2.0, "extra": "fails"})

    # Obey FrozenMixin
    with pytest.raises(ValidationError):
        coord.x = 99.0

    # 3. Leaf model can selectively override any of these settings
    class DynamicMutableModel(APIModel):
        model_config = ConfigDict(extra="allow", frozen=False)
        title: str

    mutable_instance = DynamicMutableModel(title="Initial", extra_tag="Allowed")
    mutable_instance.title = "Modified"  # Mutation succeeds (overrode frozen=True)
    assert mutable_instance.title == "Modified"
    assert getattr(mutable_instance, "extra_tag") == "Allowed"  # Extra key succeeds (overrode extra="forbid")