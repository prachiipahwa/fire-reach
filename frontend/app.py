import gradio as gr
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.agent import run_agent

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def run_gradio_agent(company, icp, email):
    logs = ""
    brief = ""
    outreach_email = ""
    
    generator = run_agent(company, icp, email)
    
    for state_update in generator:
        status = state_update.get("status")
        message = state_update.get("message", "")
        
        if message:
            logs += message + "\n\n"
            
        if status == "final_brief":
            brief = state_update.get("data", "")
        elif status == "final_email":
            outreach_email = state_update.get("data", "")
            
        yield logs, brief, outreach_email

with gr.Blocks(title="FireReach Agent", theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="blue")) as demo:
    gr.Markdown("# 🔥 FireReach – Autonomous Outreach Agent")
    gr.Markdown("A lightweight python-native agentic web application.")
    
    with gr.Row():
        with gr.Column(scale=1):
            company = gr.Textbox(label="Target Company Name", value="ExampleAI")
            icp = gr.Textbox(label="Ideal Customer Profile (ICP)", value="B2B SaaS companies needing cloud cost optimization.", lines=3)
            email = gr.Textbox(label="Recipient Email", value="test@example.com")
            btn = gr.Button("Run Agent 🚀", variant="primary")
        
        with gr.Column(scale=2):
            logs_out = gr.Textbox(label="Agent Reasoning Log", lines=15, interactive=False)
            brief_out = gr.Textbox(label="Account Brief", lines=5, interactive=False)
            email_out = gr.Textbox(label="Outreach Email", lines=8, interactive=False)
            
    btn.click(fn=run_gradio_agent, inputs=[company, icp, email], outputs=[logs_out, brief_out, email_out])
    
if __name__ == "__main__":
    demo.launch(server_port=8501, server_name="0.0.0.0")
