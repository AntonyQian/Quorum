from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def api_error(status: int, code: str, message: str) -> HTTPException:
    """Error body per SPEC §3: {"detail": {"code": ..., "message": ...}}."""
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def not_found(what: str = "Resource") -> HTTPException:
    return api_error(404, "not_found", f"{what} not found")


def forbidden(message: str = "Not allowed") -> HTTPException:
    return api_error(403, "forbidden", message)


# Framework errors (unknown route, wrong method, bad path/query/body) re-shaped to the SPEC §3 error body.

_CODE_FOR_STATUS = {401: "forbidden", 403: "forbidden", 404: "not_found"}


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and {"code", "message"} <= set(exc.detail):
        detail = exc.detail
    else:
        detail = {"code": _CODE_FOR_STATUS.get(exc.status_code, "invalid_request"), "message": str(exc.detail)}
    return JSONResponse({"detail": detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    parts = []
    for err in exc.errors():
        where = ".".join(str(p) for p in err.get("loc", ()))
        parts.append(f"{where}: {err.get('msg', 'invalid')}" if where else err.get("msg", "invalid"))
    message = "; ".join(parts) or "Invalid request"
    return JSONResponse({"detail": {"code": "invalid_request", "message": message}}, status_code=422)


def install(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
