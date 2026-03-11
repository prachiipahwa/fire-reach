from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import json
import logging
from .agent import run_agent

app = FastAPI(title="FireReach Agent API")

logger = logging.getLogger("uvicorn.error")

class AgentRequest(BaseModel):
    target_company: str
    icp: str
    recipient_email: str

@app.post("/api/run-agent")
async def run_agent_endpoint(request: AgentRequest):
    """
    Streams the agent reasoning steps back to the client using Server-Sent Events.
    """
    def event_stream():
        try:
            generator = run_agent(request.target_company, request.icp, request.recipient_email)
            for state_update in generator:
                yield f"data: {json.dumps(state_update)}\n\n"
        except Exception as e:
            error_payload = {"status": "error", "message": f"Server Error: {str(e)}"}
            yield f"data: {json.dumps(error_payload)}\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/health")
def health_check():
    return {"status": "healthy"}
