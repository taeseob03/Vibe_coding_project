from fastapi import Request
from fastapi.responses import JSONResponse


async def same_origin_writes(request: Request, call_next):
    """쿠키를 사용하는 변경 요청은 다른 웹사이트에서 보내지 못하게 합니다.

    브라우저가 아닌 로컬 API 도구의 Origin 없는 요청은 허용합니다.
    """
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        own_origin = f"{request.url.scheme}://{request.url.netloc}"
        if request.headers.get("sec-fetch-site") == "cross-site" or (
            origin is not None and origin.rstrip("/") != own_origin
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "CROSS_ORIGIN_DENIED",
                        "message": "같은 사이트에서 다시 시도해 주세요.",
                    }
                },
            )
    return await call_next(request)
