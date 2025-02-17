class ProjectAlreadyOpenError(Exception):
    """Raised when the project is already open."""
    pass

class ProjectNotFoundError(Exception):
    """Raised when the project file is not found."""
    pass

class NotFullyInitializedError(Exception):
    """Raised when the parameter is not fully initialized"""
    pass