import os
import smtplib
from email.message import EmailMessage
import json

# Placeholder for LLM client to be used inside tools if needed.
# Since we want it to be fast and use groq/gemini dynamically, we can pass the client or initialize it.
import os
from typing import Dict, Any, List

from duckduckgo_search import DDGS
from datetime import datetime

class ToolSignalHarvesterError(Exception):
    pass

def tool_signal_harvester(company: str) -> str:
    """
    TOOL 1: Deterministic Signal Harvester
    Purpose: Fetch real signals about a given company using live web search.
    This does NOT use LLM reasoning. Returns structured JSON data.
    """
    
    try:
        # Search for recent news and info about the company
        query = f'"{company}" news OR funding OR hiring OR launch'
        results = DDGS().text(query, max_results=5)
        
        signals = []
        if results:
            for r in results:
                title = r.get("title", "")
                snippet = r.get("body", "")
                signals.append(f"{title}: {snippet}")
        
        if not signals:
             signals = [f"No recent notable public signals found for {company} in the last 30 days."]

        result = {
            "company": company,
            "signals": signals,
            "harvested_at": datetime.now().isoformat()
        }
        return json.dumps(result)
        
    except Exception as e:
        # Fallback if DDGS is rate limited
         result = {
            "company": company,
            "signals": [f"Error harvesting live signals: {str(e)}"],
            "harvested_at": datetime.now().isoformat()
        }
         return json.dumps(result)

def invoke_llm_for_tool(prompt: str) -> str:
    """Helper to invoke LLM locally for tool reasoning."""
    provider = os.getenv("LLM_PROVIDER", "GROQ").upper()
    
    if provider == "GROQ":
        import groq
        client = groq.Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    else:
        # Fallback Gemini
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text

def tool_research_analyst(signals_json: str, icp: str) -> str:
    """
    TOOL 2: AI Research Analyst
    Purpose: Output a 2-paragraph Account Brief connecting signals with ICP strategically.
    """
    prompt = f"""
    You are an expert sales researcher. 
    Here are the company signals: {signals_json}
    Here is our Ideal Customer Profile (ICP): {icp}
    
    Write EXACTLY a 2-paragraph Account Brief.
    - Paragraph 1: Explain the pain points derived from the signals.
    - Paragraph 2: Explain why outreach from our ICP is highly relevant to them right now.
    
    Do NOT include any pleasantries, just the 2 paragraphs.
    """
    brief = invoke_llm_for_tool(prompt)
    return brief

def tool_outreach_automated_sender(account_brief: str, signals_json: str, target_email: str) -> str:
    """
    TOOL 3: Automated Sender (Execution)
    Purpose: Generate a highly personalized email and send via SMTP.
    """
    prompt = f"""
    You are an elite B2B SDR.
    Write a highly personalized short, punchy cold email.
    Use this account brief for context: {account_brief}
    Signals to reference: {signals_json}
    
    You MUST EXPLICITLY reference the captured signals in the email (e.g., "I noticed you're hiring for 5 new engineering roles...").
    Output ONLY the email body (no subject line, no placeholders like [Your Name]). 
    Sign it off simply as 'Best, Alex'.
    """
    
    email_body = invoke_llm_for_tool(prompt)
    
    # Send email
    smtp_server = os.getenv("SMTP_SERVER", "smtp.ethereal.email")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    
    msg = EmailMessage()
    msg.set_content(email_body)
    msg['Subject'] = "Ideas regarding your recent initiatives"
    msg['From'] = smtp_user if smtp_user else "agent@firereach.ai"
    msg['To'] = target_email
    
    status = f"Email drafted to {target_email}:\n\n{email_body}\n\n"
    
    try:
        if smtp_user and smtp_pass and smtp_user != "your_ethereal_user":
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            status += "[SUCCESS: Sent via SMTP]"
        else:
            status += "[SIMULATION: SMTP credentials not set or using defaults, did not actually send]"
    except Exception as e:
         status += f"[ERROR sending SMTP: {str(e)}]"
         
    return status

# Mapping for the agent
AVAILABLE_TOOLS = {
    "tool_signal_harvester": tool_signal_harvester,
    "tool_research_analyst": tool_research_analyst,
    "tool_outreach_automated_sender": tool_outreach_automated_sender
}
