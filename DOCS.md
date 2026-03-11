# FireReach Documentation

## System Architecture

FireReach is an autonomous outreach agent prototype designed for high performance and efficiency using a monolithic native Python web app structure.
- **Frontend**: Gradio (Native Python UI, fulfilling the user's explicit request for a fully Python-native stack, acting as the minimal dashboard).
- **Backend Core**: A Python Generator function (`run_agent`) that maintains a ReAct-style stateless loop using explicit JSON output constraints, making it robust against varying LLM implementations (works with Groq/Llama or Gemini).
- **Backend API**: A FastAPI app in `backend/main.py` is included to fulfill the FastAPI requirement natively if HTTP streaming endpoints are desired.

## Tool Schemas

The agent is strictly instructed to use only three tools sequentially:

### 1. `tool_signal_harvester` (Deterministic)
- **Purpose**: Fetch real signals about a given company. Does NOT use LLM reasoning.
- **Input Object**: `{"company": "string"}`
- **Output**: JSON string containing `company` and an array of `signals`.

### 2. `tool_research_analyst` (AI Reasoning)
- **Purpose**: Create a 2-paragraph Account Brief connecting signals with the ICP strategically.
- **Input Object**: `{"signals_json": "string", "icp": "string"}`
- **Output**: String containing exactly two paragraphs explaining pain points and relevance.

### 3. `tool_outreach_automated_sender` (Execution)
- **Purpose**: Generate a highly personalized short email referencing signals, and automatically send it to the prospect via SMTP.
- **Input Object**: `{"account_brief": "string", "signals_json": "string", "target_email": "string"}`
- **Output**: Status string confirming email dispatch (via Ethereal mock, real SMTP, or simulation fallback) with the drafted body.

## Logic Flow

1. The user provides Target Company, ICP, and Recipient Email via the UI.
2. The `run_agent` loop starts and injects the `SYSTEM_PROMPT` along with the user data.
3. The LLM processes the system context and outputs a JSON action containing its `thought`, the name of the tool, and the arguments.
4. The loop parses the JSON, executes the corresponding tool in `backend/tools.py`.
5. The result of the tool is appended back to the dialogue state as `User: Tool Output: <result>`.
6. This cycle repeats strictly sequentially (`signal_harvester` -> `research_analyst` -> `outreach_automated_sender`), maintaining the reasoning state, until the LLM outputs `"tool": "DONE"`.

## System Prompt

The system prompt strictly binds the LLM into a sequential state machine by explicitly passing the JSON schema required to proceed at each step:

```text
You are FireReach, an elite Autonomous Outreach Agent.
Your master objective is to research a target company, generate contextual outreach intelligence, and automatically send an email.

You must sequentially use these EXACT three tools, in this order:
1. tool_signal_harvester
2. tool_research_analyst
3. tool_outreach_automated_sender

... (Input details provided here) ...

At each step, output a JSON object with this exact schema:
{
  "thought": "<your reasoning for what to do next>",
  "tool": "<name of tool to call, OR 'DONE' if all 3 tools are completely finished>",
  "args": {
    "<arg_name>": "<arg_value>"
  }
}
```

This prompt format guarantees correct tool invocation without requiring complex package-specific wrapper functions, making the core agent framework highly portable, deterministic, and fast.
