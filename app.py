from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from import_folder.mcp_server import mcp_app


from errors.user import AppError
from routers import (
    ai_chat,
    auth,
    calories,
    chat_message,
    files,
    github,
    users,
    chat_session,
    skills
)
from repositories.slack_bot import handler

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

load_dotenv()

# ------------------------------------------------------------------
# FastAPI
# ------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_app.lifespan(app):
        yield


app = FastAPI(lifespan=lifespan)

# ------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://python-react-ehkr-git-main-stoianlucians-projects.vercel.app",
        "https://python-react-ehkr.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# print(FastMCP.__version__, "========")

# ------------------------------------------------------------------
# Exception handlers
# ------------------------------------------------------------------


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.message,
            "errorCode": exc.error_code,
        },
    )

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------


@app.post("/slack/events")
async def slack_events(request: Request):
    return await handler.handle(request)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(ai_chat.router)
app.include_router(chat_session.router)
app.include_router(chat_message.router)
app.include_router(skills.router)
app.include_router(github.router)
app.include_router(calories.router)
app.mount("/mcp", mcp_app)
