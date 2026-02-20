from fastapi import FastAPI
from errors.user import AppError
from routers import users, auth
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi import HTTPException

app = FastAPI()

# ----- CORS middleware -----
origins = [
    "http://localhost:5173",
    "http://localhost:5173/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,     # exact dev origins, or ["*"] for quick dev
    allow_credentials=True,    # needed if you send cookies/auth headers
    allow_methods=["*"],       # allows GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],       # allows any headers
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.message,
            "errorCode": exc.error_code
        },
    )

# /users
app.include_router(users.router)
# /auth
app.include_router(auth.router)