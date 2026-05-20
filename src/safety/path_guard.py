from pathlib import Path


class PathGuardError(Exception):
    """Raised when a requested file path violates the safety policy."""
    pass


class PathGuard:
    """
    PathGuard controls what the Victim Agent is allowed to read.

    Current rule:
    - The Victim Agent may only access files inside data/inputs/.
    - Any path outside data/inputs/ must be blocked.
    """

    def __init__(self, allowed_root: str = "data/inputs"):
        # Resolve the project root based on the current working directory.
        self.project_root = Path.cwd().resolve()

        # Define the only allowed absolute directory prefix.
        self.allowed_root = (self.project_root / allowed_root).resolve()

    def resolve_allowed_path(self, requested_path: str) -> Path:
        """
        Convert the Agent's requested path into an absolute path and verify
        that it stays inside the allowed sandbox directory.

        If the path attempts to escape the sandbox, raise PathGuardError.
        This check happens regardless of whether the target file exists.
        """

        if not requested_path or not isinstance(requested_path, str):
            raise PathGuardError("Invalid path: path must be a non-empty string.")

        requested = Path(requested_path)

        # If the Agent provides a relative path, resolve it from the project root.
        if not requested.is_absolute():
            requested = self.project_root / requested

        # Canonicalize the path. This removes ../, ./, and resolves symlinks.
        try:
            resolved_path = requested.resolve()
        except Exception as e:
            raise PathGuardError(f"Path canonicalization failed: {str(e)}")

        # Core security check:
        # The final resolved path must remain inside the allowed root directory.
        try:
            resolved_path.relative_to(self.allowed_root)
        except ValueError:
            # Anything outside data/inputs/ is treated as an access violation,
            # even if the file does not actually exist.
            raise PathGuardError(
                f"Blocked path: {requested_path} is outside allowed directory"
            )

        # Do not check file existence here.
        # Existence checks belong in file_reader.py.
        # This keeps access-control failures separate from file-not-found errors.
        return resolved_path


def is_path_allowed(requested_path: str) -> bool:
    """
    Minimal helper function for tests.

    Returns True if the path is allowed.
    Returns False if the path is blocked or invalid.
    """

    guard = PathGuard()

    try:
        guard.resolve_allowed_path(requested_path)
        return True
    except PathGuardError:
        return False
