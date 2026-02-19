from fastapi import FastAPI
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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # asiguram ca detail este dict
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content=detail
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # erori neașteptate → JSON standard
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "code": "internal_error"}
    )

# /users
app.include_router(users.router)
# /auth
app.include_router(auth.router)