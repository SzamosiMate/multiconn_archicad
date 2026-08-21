class _Registry:
    mixins: tuple[type, ...] = ()
    locked: bool = False


def configure(*mixins: type):
    """
    Configure the behavior of the API models by injecting Mixins.

    MUST be called before importing any models from the package.
    Example: `configure(StrictValidationMixin, FrozenMixin)`
    """
    if _Registry.locked:
        raise RuntimeError(
            "archicad_models configure() was called AFTER model classes were already built "
            "(something imported the models before you configured it). "
            "Call configure() before any multiconn_archicad model imports."
        )
    _Registry.mixins = mixins