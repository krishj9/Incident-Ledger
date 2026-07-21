class RepositoryError(Exception):
    """Base repository exception."""
    pass


class StaleVersionError(RepositoryError):
    """Raised when an optimistic concurrency check fails."""
    pass


class EntityNotFoundError(RepositoryError):
    """Raised when an entity is not found."""
    pass
