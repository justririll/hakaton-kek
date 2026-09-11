from fastapi import FastAPI

from app.routers.health import router as health_router

app = FastAPI(
    title="FastAPI Starter",
    description="A FastAPI application managed with uv.",
    version="0.1.0",
)
app.include_router(health_router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {"message": "Welcome to FastAPI", "docs": "/docs"}
