from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from errors.user import AppError
from routers import auth, files, users, aiChat, test

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

load_dotenv()

app = FastAPI()
# ----- CORS middleware -----

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://python-react-ehkr-git-main-stoianlucians-projects.vercel.app",
        "https://python-react-ehkr.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
# /files
app.include_router(files.router)
# /chat
app.include_router(aiChat.router)
# /test
app.include_router(test.router)
