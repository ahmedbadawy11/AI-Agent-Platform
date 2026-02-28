"""
Chat and voice endpoints: list messages, send text (optional stream), send voice (audio upload).
"""
import json
from base64 import b64encode

from fastapi import APIRouter, Request, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, JSONResponse

from controllers import conversation
from routes.schemes import SendMessageRequest, MessageResponse, ErrorResponse

chat_router = APIRouter()


def get_db(request: Request):
    return request.app.db_client


def get_openai_provider(request: Request):
    return getattr(request.app, "openai_provider", None)


@chat_router.get("/styles", summary="List available response styles with descriptions")
async def list_styles():
    return [
        {"value": key, "description": desc}
        for key, desc in conversation.STYLE_DESCRIPTIONS.items()
    ]


@chat_router.get("/session-messages", summary="List messages in a session", response_model=list[MessageResponse])
async def list_messages(request: Request, session_id: int = Query(..., description="Session ID")):
    return await conversation.get_messages(get_db(request), session_id)


@chat_router.post(
    "/send-message",
    summary="Send a text message; returns assistant reply (JSON)",
    response_model=MessageResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def send_text_message(request: Request, body: SendMessageRequest):
    provider = get_openai_provider(request)
    if provider is None:
        return JSONResponse(status_code=503, content=ErrorResponse(detail="LLM provider not available").model_dump())
    out = await conversation.send_text_message(get_db(request), provider, body.session_id, body.content, style=body.style)
    if out is None:
        return JSONResponse(status_code=404, content=ErrorResponse(detail="Session not found or LLM error").model_dump())
    return out


@chat_router.post("/stream-message", summary="Send a text message; stream assistant reply (SSE)", responses={503: {"model": ErrorResponse}})
async def send_text_message_stream(request: Request, body: SendMessageRequest):
    """Stream LLM response as Server-Sent Events. Each event: data: {\"content\": \"chunk\"}. Final event: data: {\"done\": true}."""
    provider = get_openai_provider(request)
    if provider is None:
        return JSONResponse(status_code=503, content=ErrorResponse(detail="LLM provider not available").model_dump())
    gen = conversation.stream_text_message(get_db(request), provider, body.session_id, body.content, style=body.style)
    return StreamingResponse(gen, media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@chat_router.post("/send-voice-message", summary="Send voice message; streams SSE with text + audio", responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
async def send_voice_message(
    request: Request,
    session_id: int = Form(..., description="Session ID"),
    audio: UploadFile = File(..., description="Audio file (e.g. webm, mp3)"),
    style: str | None = Form(None, description="Response style"),
):
    provider = get_openai_provider(request)
    if provider is None:
        return JSONResponse(status_code=503, content=ErrorResponse(detail="LLM provider not available").model_dump())
    filename = audio.filename or "audio.webm"
    content = await audio.read()

    stt_text, stt_error = conversation.run_voice_stt(provider, content, filename)
    if stt_error:
        status = 400 if "no text" in stt_error.lower() or "speech-to-text" in stt_error.lower() else 500
        return JSONResponse(status_code=status, content=ErrorResponse(detail=stt_error).model_dump())

    async def sse_generator():
        async for event_type, data in conversation.stream_voice_after_stt(
            get_db(request), provider, session_id, stt_text, style=style
        ):
            if event_type == "audio":
                yield f"data: {json.dumps({'type': 'audio', 'chunk': b64encode(data).decode()})}\n\n"
            elif event_type == "user_text":
                yield f"data: {json.dumps({'type': 'user_text', 'content': data})}\n\n"
            elif event_type == "assistant_text":
                yield f"data: {json.dumps({'type': 'assistant_text', 'content': data})}\n\n"
            elif event_type == "error":
                yield f"data: {json.dumps({'type': 'error', 'content': data})}\n\n"
            elif event_type == "done":
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
