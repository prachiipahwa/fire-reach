import os
import json
from .tools import AVAILABLE_TOOLS

SYSTEM_PROMPT = """You are FireReach, an elite Autonomous Outreach Agent.
Your master objective is to research a target company, generate contextual outreach intelligence, and automatically send an email.

You must sequentially use these EXACT three tools, in this order:
1. tool_signal_harvester
2. tool_research_analyst
3. tool_outreach_automated_sender

You are provided with:
- Target Company Name
- User ICP (Ideal Customer Profile)
- Recipient Email

At each step, output a JSON object with this exact schema:
{
  "thought": "<your reasoning for what to do next>",
  "tool": "<name of tool to call, OR 'DONE' if all 3 tools are completely finished>",
  "args": {
    "<arg_name>": "<arg_value>"
  }
}

Available Tools and their exact arguments:
- tool_signal_harvester: 
    args: {"company": "<name>"}
- tool_research_analyst:
    args: {"signals_json": "<raw json string returned by harvester>", "icp": "<user_icp>"}
- tool_outreach_automated_sender:
    args: {"account_brief": "<brief output by analyst>", "signals_json": "<raw json string returned by harvester>", "target_email": "<recipient_email>"}

You must maintain your context. When a tool returns a result, we will append it to the conversation.
Only output ONLY JSON. No markdown wrappings, no other text. Just parseable JSON.
"""

def generate_agent_response(messages: list) -> dict:
    provider = os.getenv("LLM_PROVIDER", "GROQ").upper()
    try:
        if provider == "GROQ":
            import groq
            client = groq.Groq(api_key=os.getenv("GROQ_API_KEY", ""))
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        else:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
            
            # Convert messages to Gemini format roughly
            gemini_msgs = []
            for m in messages:
                role = "user" if m["role"] == "user" else "model"
                gemini_msgs.append({"role": role, "parts": [{"text": m["content"]}]})
                
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=gemini_msgs,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            return json.loads(response.text)
    except Exception as e:
        return {"thought": f"Error calling LLM: {str(e)}", "tool": "DONE", "args": {}}

def run_agent(target_company: str, icp: str, recipient_email: str):
    """
    Generator yielding state updates so the frontend can stream logs.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Target Company: {target_company}\nICP: {icp}\nRecipient Email: {recipient_email}\nBegin your task by logically deciding the first step."}
    ]
    
    steps_taken = 0
    max_steps = 5  # Failsafe limit
    
    yield {"status": "started", "message": "Agent initialized and prompt loaded."}
    
    while steps_taken < max_steps:
        # Call LLM to get next action
        action_json = generate_agent_response(messages)
        
        thought = action_json.get("thought", "No thought provided")
        tool_name = action_json.get("tool", "DONE")
        args = action_json.get("args", {})
        
        yield {"status": "thought", "message": f"🤖 Thought: {thought}"}
        
        if tool_name == "DONE":
            yield {"status": "completed", "message": "✅ Agent task completed successfully."}
            break
            
        if tool_name not in AVAILABLE_TOOLS:
            yield {"status": "error", "message": f"❌ Tool '{tool_name}' not found."}
            break
            
        yield {"status": "tool_call", "message": f"🛠️ Calling {tool_name} with args: {args}"}
        
        try:
            # Execute tool
            tool_func = AVAILABLE_TOOLS[tool_name]
            result = tool_func(**args)
            
            yield {"status": "tool_result", "message": f"📄 Result from {tool_name}: {str(result)[:500]}..."}
            
            # Append interaction to memory
            messages.append({"role": "assistant", "content": json.dumps(action_json)})
            messages.append({"role": "user", "content": f"Tool Output: {result}"})
            
            # Pass final payload specifically for frontend rendering
            if tool_name == "tool_research_analyst":
                yield {"status": "final_brief", "data": result}
            elif tool_name == "tool_outreach_automated_sender":
                yield {"status": "final_email", "data": result}
                
        except Exception as e:
            yield {"status": "error", "message": f"❌ Error executing {tool_name}: {str(e)}"}
            break
            
        steps_taken += 1
        
    if steps_taken >= max_steps:
         yield {"status": "error", "message": "❌ Agent exceeded maximum step limit."}
