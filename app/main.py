from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time

from app.core.config import settings
from app.core.exceptions import AppError
from app.routers import (auth, users , freelancer_profiles , skills , jobs , proposals , contracts , milestones , reviews)

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Upwork-style Freelancer Marketplace backend. "
        "Two roles: CLIENT and FREELANCER. "
        "Full workflow: jobs -> proposals -> contracts -> milestones -> reviews."
    ),
    version="0.1.0",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    print(
        f"{request.method} {request.url.path} "
        f"-> {response.status_code} "
        f"({process_time:.4f}s)"
    )
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )


@app.get("/health", tags=["health"])
def health_check() -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(skills.router)
app.include_router(freelancer_profiles.router)
app.include_router(jobs.router)
app.include_router(proposals.router)
app.include_router(contracts.router)
app.include_router(milestones.router)
app.include_router(reviews.router)
