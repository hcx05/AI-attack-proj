from src.safety.path_guard import PathGuard, PathGuardError


class FileReaderError(Exception):
    """Raised when the file reader cannot safely read a file."""
    pass


class FileReader:
    """
    Restricted file reader for the Victim Agent.

    This tool does not decide whether a path is safe by itself.
    Before reading any file, it delegates path validation to PathGuard.
    """

    def __init__(self):
        self.path_guard = PathGuard()

    def read_file(self, requested_path: str) -> dict:
        """
        Safely read a file if the requested path is allowed.

        Returns a structured dictionary so the Orchestrator can easily
        determine whether the read was allowed, blocked by security policy,
        or failed because of a normal system error.
        """

        try:
            # 1. Ask PathGuard to validate the requested path.
            # If the path is allowed, PathGuard returns a safe absolute Path object.
            safe_path = self.path_guard.resolve_allowed_path(requested_path)

            # 2. Only after the path passes security validation do we check
            # whether the file actually exists.
            if not safe_path.exists():
                raise FileReaderError(f"File not found: {requested_path}")

            if not safe_path.is_file():
                raise FileReaderError(f"Path is not a file: {requested_path}")

            # 3. Read the actual file content.
            content = safe_path.read_text(encoding="utf-8")

            return {
                "status": "allowed",
                "requested_path": requested_path,
                "resolved_path": str(safe_path),
                "content": content,
                "error": None,
            }

        except PathGuardError:
            # Security block:
            # The Agent attempted to access a path outside the allowed sandbox.
            #
            # Do not return internal absolute paths or detailed guard errors
            # to the Agent, because that could leak host filesystem information.
            return {
                "status": "blocked",
                "requested_path": requested_path,
                "resolved_path": None,
                "content": None,
                "error": "Access Denied: Requested path violates safety boundary policy.",
            }

        except FileReaderError as e:
            # Normal file read error:
            # The path is inside the sandbox, but the file does not exist
            # or is not a regular file.
            return {
                "status": "error",
                "requested_path": requested_path,
                "resolved_path": None,
                "content": None,
                "error": str(e),
            }

        except Exception:
            # Unexpected error:
            # Keep the tool from crashing, but do not expose internal details
            # back to the Agent.
            return {
                "status": "error",
                "requested_path": requested_path,
                "resolved_path": None,
                "content": None,
                "error": "Unexpected file reader error.",
            }


def read_file(requested_path: str) -> dict:
    """
    Convenience helper for tests and simple tool calls.
    """

    reader = FileReader()
    return reader.read_file(requested_path)
