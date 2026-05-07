from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from errors.user import AppError
from routers import auth, files, users, aiChat, test

load_dotenv()

app = FastAPI()
# ----- CORS middleware -----
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",  # same dev server, different host string in the browser
    "https://python-react-ehkr-git-main-stoianlucians-projects.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
# /files
app.include_router(files.router)
# /chat
app.include_router(aiChat.router)
# /test
app.include_router(test.router)
