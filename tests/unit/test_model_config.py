import sys
import subprocess
import pytest
from pydantic import ValidationError


# =========================================================================
# REQUIREMENT 1: configure() raises if models are already imported
# =========================================================================

def test_configure_after_import_raises_runtime_error(clean_models):
    """Verifies that the lock triggers immediately if configure() is called late."""
    from multiconn_archicad.models.config import configure

    # 1. Import a model class -> triggers __init_subclass__ -> locks registry
    import multiconn_archicad.models.tapir.commands

    # 2. Attempting to configure now MUST fail loudly
    with pytest.raises(RuntimeError, match="called AFTER model classes were already built"):
        configure()


def test_lock_enforcement_in_isolated_process():
    """Airtight subprocess test: simulates a user making an import-order mistake in a real script."""
    code = """
import multiconn_archicad.models.tapir.commands
from multiconn_archicad.models.config import configure
from multiconn_archicad.models.mixins import StrictValidationMixin

# This must raise RuntimeError and exit with an error code
configure(StrictValidationMixin)
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode != 0
    assert "called AFTER model classes were already built" in result.stderr


def test_importing_base_locks_registry_immediately(clean_models):
    """
    Verifies that importing base.py (which compiles APIModel)
    immediately locks the registry before any subclass is even defined.
    """
    from multiconn_archicad.models.config import configure

    # 1. Import base directly (APIModel compiles here)
    import multiconn_archicad.models.base

    # 2. Calling configure now MUST raise RuntimeError immediately
    with pytest.raises(RuntimeError, match="called AFTER model classes were already built"):
        configure()


# =========================================================================
# REQUIREMENT 2: Importing config / root library does NOT load models
# =========================================================================

def test_importing_config_does_not_lock_or_import_models(clean_models):
    """Verifies that importing config.py is completely passive."""
    # 1. Import config
    import multiconn_archicad.models.config as config

    # 2. Ensure lock is NOT engaged
    assert config._Registry.locked is False

    # 3. Ensure no model files were transitively loaded into sys.modules
    assert "multiconn_archicad.models.base" not in sys.modules
    assert "multiconn_archicad.models.types" not in sys.modules
    assert "multiconn_archicad.models.commands" not in sys.modules


# =========================================================================
# REQUIREMENT 3: Mixins properly alter model behavior
# =========================================================================

def test_strict_validation_mixin_alters_behavior(clean_models):
    """Verifies StrictValidationMixin rejects unknown keys but respects context bypass."""
    from multiconn_archicad.models.config import configure
    from multiconn_archicad.models.mixins import StrictValidationMixin

    # Configure strict mode
    configure(StrictValidationMixin)

    from multiconn_archicad.models.tapir.types import Coordinate2D

    # 1. Unknown field -> Must raise ValueError
    with pytest.raises(ValueError, match="Extra fields not allowed in Coordinate2D"):
        Coordinate2D(x=1.0, y=2.0, fake_z_coordinate=3.0)

    # 2. Context bypass -> Must safely ignore unknown field
    valid_with_context = Coordinate2D.model_validate(
        {"x": 1.0, "y": 2.0, "future_api_field": "test"},
        context={"ignore_extra_keys": True}
    )
    assert valid_with_context.x == 1.0


def test_frozen_mixin_alters_behavior(clean_models):
    """Verifies FrozenMixin makes models immutable and hashable."""
    from multiconn_archicad.models.config import configure
    from multiconn_archicad.models.mixins import FrozenMixin

    configure(FrozenMixin)

    from multiconn_archicad.models.tapir.types import Coordinate2D

    coord = Coordinate2D(x=10.0, y=20.0)

    # 1. Mutation must raise ValidationError
    with pytest.raises(ValidationError):
        coord.x = 99.0

    # 2. Must be hashable (usable in sets / dict keys)
    coord_set = {coord}
    assert coord in coord_set


def test_omit_defaults_mixin_alters_behavior(clean_models):
    """Verifies OmitDefaultsMixin excludes default values from dumps."""
    from multiconn_archicad.models.config import configure
    from multiconn_archicad.models.mixins import OmitDefaultsMixin

    configure(OmitDefaultsMixin)

    from multiconn_archicad.models.tapir.types import BeamData, Coordinate2D

    # BeamData has many optional fields defaulting to None (e.g. offset, slantAngle)
    beam = BeamData(
        begCoordinate=Coordinate2D(x=0.0, y=0.0),
        endCoordinate=Coordinate2D(x=5.0, y=0.0),
        zCoordinate=0.0,
    )

    dumped = beam.model_dump()

    # Defaults like slantAngle (None) should be omitted
    assert "slantAngle" not in dumped
    assert "begCoordinate" in dumped


def test_multiple_mixins_combine_cooperatively(clean_models):
    """
    Verifies that all 4 mixins (Strict, Frozen, StripWhitespace, OmitDefaults)
    can be configured together and that all their behaviors execute simultaneously.
    """
    from multiconn_archicad.models.config import configure
    from multiconn_archicad.models.mixins import (
        StrictValidationMixin,
        FrozenMixin,
        StripWhitespaceMixin,
        OmitDefaultsMixin,
    )

    # 1. Configure with all 4 mixins simultaneously
    configure(
        StrictValidationMixin,
        FrozenMixin,
        StripWhitespaceMixin,
        OmitDefaultsMixin,
    )

    from multiconn_archicad.models.tapir.types import DetailData, BeamData, Coordinate2D

    # =========================================================================
    # BEHAVIOR 1: StripWhitespaceMixin (Trims whitespace from strings)
    # =========================================================================
    detail = DetailData(
        name="   Foundation Detail A-A   ",
        referenceId="   DET-001   ",
    )
    assert detail.name == "Foundation Detail A-A"
    assert detail.referenceId == "DET-001"

    # =========================================================================
    # BEHAVIOR 2: StrictValidationMixin (Rejects unknown parameters)
    # =========================================================================
    with pytest.raises(ValueError, match="Extra fields not allowed in DetailData"):
        DetailData(
            name="Roof Section",
            referenceId="DET-002",
            hallucinated_param="invalid_field",
        )

    # =========================================================================
    # BEHAVIOR 3: FrozenMixin (Immutable & Hashable)
    # =========================================================================
    # Mutating an attribute must raise a Pydantic ValidationError
    with pytest.raises(ValidationError):
        detail.name = "Changed Name"

    # Must be hashable so it can be added to sets and used as dict keys
    detail_set = {detail}
    assert detail in detail_set

    # =========================================================================
    # BEHAVIOR 4: OmitDefaultsMixin (Default/None values excluded from dumps)
    # =========================================================================
    beam = BeamData(
        begCoordinate=Coordinate2D(x=0.0, y=0.0),
        endCoordinate=Coordinate2D(x=10.0, y=0.0),
        zCoordinate=0.0,
        # offset, slantAngle, arcAngle, etc. default to None
    )
    dumped = beam.model_dump()

    assert "begCoordinate" in dumped
    assert "offset" not in dumped
    assert "slantAngle" not in dumped
    assert "arcAngle" not in dumped


def test_extra_allow_models_permit_arbitrary_keys_under_strict_mode(clean_models):
    """
    Verifies that models explicitly configured with extra='allow' (AddOnCommandParameters
    and AddOnCommandResponse) continue to accept arbitrary keys, even when StrictValidationMixin
    is globally enabled.
    """
    from multiconn_archicad.models.config import configure
    from multiconn_archicad.models.mixins import StrictValidationMixin

    # 1. Enable strict validation globally
    configure(StrictValidationMixin)

    # Import both standard models and the Add-On models
    from multiconn_archicad.models.tapir.types import Coordinate2D
    from multiconn_archicad.models.official.types import (
        AddOnCommandParameters,
        AddOnCommandResponse,
    )

    # =========================================================================
    # 1. Verify that standard models are STILL strictly locked down
    # =========================================================================
    with pytest.raises(ValueError, match="Extra fields not allowed in Coordinate2D"):
        Coordinate2D(x=1.0, y=2.0, forbidden_key="must_fail")

    # =========================================================================
    # 2. Verify AddOnCommandParameters allows arbitrary input keys
    # =========================================================================
    custom_params = AddOnCommandParameters.model_validate({
        "customAddonKey": "customValue",
        "nestedData": {"flag": True, "count": 42},
        "targetStory": 1,
    })

    dumped_params = custom_params.model_dump()
    assert dumped_params["customAddonKey"] == "customValue"
    assert dumped_params["nestedData"] == {"flag": True, "count": 42}
    assert dumped_params["targetStory"] == 1

    # =========================================================================
    # 3. Verify AddOnCommandResponse allows arbitrary response keys
    # =========================================================================
    custom_response = AddOnCommandResponse.model_validate({
        "status": "OK",
        "returnedGuids": ["uuid-1234", "uuid-5678"],
        "executionTimeMs": 12.5,
    })

    dumped_response = custom_response.model_dump()
    assert dumped_response["status"] == "OK"
    assert dumped_response["returnedGuids"] == ["uuid-1234", "uuid-5678"]
    assert dumped_response["executionTimeMs"] == 12.5