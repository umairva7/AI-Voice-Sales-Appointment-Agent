from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


app = FastAPI(
	title="AI Voice Agent API",
	description="Phase 1 push-to-talk voice loop",
	version="1.0.0",
)


class MessageRequest(BaseModel):
	message: str


@app.get("/", include_in_schema=False)
async def frontend() -> FileResponse:
	return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
	return {"message": "API is running"}


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
	return {"status": "healthy"}


@app.post("/api/chat", tags=["Messages"])
async def chat(request: MessageRequest) -> dict[str, str]:
	message = request.message.strip()
	if not message:
		return {"reply": "I did not catch that. Please try speaking again."}

	return {
		"reply": (
			f"Thanks for sharing that. I heard: \"{message}\". "
			"The full sales assistant is coming in the next phase."
		)
	}


@app.post("/api/message", tags=["Messages"], include_in_schema=False)
async def handle_message(request: MessageRequest) -> dict[str, str]:
	return await chat(request)


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
