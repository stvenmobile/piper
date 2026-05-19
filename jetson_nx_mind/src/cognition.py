# ==============================================================================
# Component:  jetson_nx_mind
# Module:     cognition.py
# Version:    2.1.0 (Rich Deep-Dive System Prompt Evolution)
# Purpose:    Manages conversational sliding contexts and routes raw text strings
#             out to a dedicated workstation PC running Ollama on an RTX 5070.
#             System prompt expanded to unlock deep, highly informative answers.
# ==============================================================================

import os
import requests
from datetime import datetime

class CognitiveKernel:
    def __init__(self, model_name="hermes3:latest", max_turns=4):
        self.model_name = model_name
        self.max_turns = max_turns
        self.history = []  # Holds tuples of (user_msg, assistant_msg)
        self.journal_path = os.path.expanduser("~/piper/jetson_nx_mind/journal_queries.md")
        self.ollama_endpoint = "http://192.168.1.150:11434/api/chat"
        
        # EVOLVED SYSTEM PROMPT: Demands technical depth while structuring for TTS parsing
        self.system_prompt = (
            "You are Piper, an advanced autonomous robotic assistant companion speaking with Steve. "
            "Provide highly comprehensive, technically accurate, and deeply informative explanations. "
            "Do not give superficial summaries; explain the underlying mechanics, physics, or architecture of the topic. "
            "Structure your output into brief, distinct paragraphs (2-3 sentences per paragraph). "
            "Never use markdown formatting like asterisks, bullet points, or bold text, as your response "
            "must be read directly aloud by a text-to-speech engine."
        )

    def log_to_journal(self, question, answer):
        """Appends the interaction transaction out to the local markdown journal."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            file_exists = os.path.exists(self.journal_path)
            with open(self.journal_path, "a") as f:
                if not file_exists:
                    f.write("# Piper Interaction Journal\n\n")
                f.write(f"### Entry: {timestamp}\n")
                f.write(f"**Steve:** {question}\n")
                f.write(f"**Piper:** {answer}\n\n")
                f.write("---\n\n")
        except Exception as e:
            print(f"[COGNITION] Error writing to journal matrix: {e}")

    def generate_response(self, user_question):
        """Constructs context window payload and invokes external network Ollama host."""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Append historical sliding context
        for past_question, past_answer in self.history:
            messages.append({"role": "user", "content": past_question})
            messages.append({"role": "assistant", "content": past_answer})
            
        # Add the fresh incoming question
        messages.append({"role": "user", "content": user_question})
        
        print(f"[COGNITION] Routing request to Quantum PC ({self.ollama_endpoint}) using '{self.model_name}'...")
        
        try:
            response = requests.post(
                self.ollama_endpoint,
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False
                },
                timeout=30  # Bumped to 30s to allow larger token generation windows safely
            )
            
            if response.status_code == 200:
                assistant_response = response.json()["message"]["content"].strip()
                
                # Update rolling context queue
                self.history.append((user_question, assistant_response))
                if len(self.history) > self.max_turns:
                    self.history.pop(0)
                    
                # Commit permanently to local Jetson disk
                self.log_to_journal(user_question, assistant_response)
                return assistant_response
            else:
                return f"Quantum PC returned an unhandled host response state code: {response.status_code}"
                
        except Exception as e:
            print(f"[COGNITION] External network inference host connection fault: {e}")
            return "My external cognitive link to the Quantum PC host dropped offline."
