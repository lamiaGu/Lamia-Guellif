"""
Serveur FastAPI — Agent de veille académique
"""

import json
import os
from typing import AsyncGenerator

import anthropic
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from campus_agent import (
    SYSTEM_PROMPT,
    TOOLS,
    compute_current_grade,
    compute_needed_grade,
    execute_tool,
    load_data,
)

app = FastAPI(title="Agent Académique uOttawa")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_client() -> anthropic.Anthropic | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    return anthropic.Anthropic(api_key=key)


# ─── API endpoints ────────────────────────────────────────────────────────────

@app.get("/api/courses")
def get_courses(x_session_id: str = Header(...)):
    data = load_data(x_session_id)
    target = data["target_grade"]
    courses = []
    for c in data["courses"]:
        current = compute_current_grade(c["assessments"])
        needed = compute_needed_grade(c["assessments"], target)
        completed = sum(1 for a in c["assessments"] if a["grade"] is not None)
        courses.append({
            "code": c["code"],
            "name": c["name"],
            "current_grade": current,
            "needed_grade": needed,
            "completed": completed,
            "total": len(c["assessments"]),
            "assessments": c["assessments"],
        })
    return {"program": data["program"], "target": target, "courses": courses}


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


async def agent_stream(request: ChatRequest, session_id: str) -> AsyncGenerator[str, None]:
    client = get_client()
    if client is None:
        yield f"data: {json.dumps({'type': 'error', 'content': '❌ Clé API manquante. Configure ANTHROPIC_API_KEY dans Railway → Variables.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    # Reconstruire l'historique API
    api_messages = []
    for msg in request.history:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    api_messages.append({"role": "user", "content": request.message})

    try:
        while True:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=api_messages,
                thinking={"type": "adaptive"},
            )

            api_messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # Extraire et streamer le texte final
                for block in response.content:
                    if block.type == "text":
                        # Streamer mot par mot pour l'effet typing
                        words = block.text.split(" ")
                        for i, word in enumerate(words):
                            chunk = word + (" " if i < len(words) - 1 else "")
                            yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

            elif response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        yield f"data: {json.dumps({'type': 'tool', 'name': block.name})}\n\n"
                        result = execute_tool(block.name, block.input, session_id)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                api_messages.append({"role": "user", "content": tool_results})
            else:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

    except anthropic.AuthenticationError:
        yield f"data: {json.dumps({'type': 'error', 'content': 'Clé API invalide.'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@app.post("/api/chat")
async def chat(request: ChatRequest, x_session_id: str = Header(...)):
    return StreamingResponse(
        agent_stream(request, x_session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# Servir le frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")
