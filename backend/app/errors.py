from fastapi import HTTPException


def api_error(status: int, code: str, message: str) -> HTTPException:
    """Error body per SPEC §3: {"detail": {"code": ..., "message": ...}}."""
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def not_found(what: str = "Resource") -> HTTPException:
    return api_error(404, "not_found", f"{what} not found")


def forbidden(message: str = "Not allowed") -> HTTPException:
    return api_error(403, "forbidden", message)
