# ==============================================================================
# Component:  jetson_nx_mind
# Module:     brain_route.py
# Version:    3.0.0 (V3 Hybrid Cognitive Router)
# Purpose:    Provides a unified API link to route asynchronous thoughts.
#             Directs background spatial mapping to Hermes (Quantum PC)
#             and executive engineering requests to Gemini Flash (Cloud).
# ==============================================================================

import os
import requests
from datetime import datetime

class CognitiveRouter:
    def __init__(self):
        self.base_dir = os.path.expanduser("~/piper/jetson_nx_mind")
        self.journal_path = os.path.join(self.base_dir, "daily_journal.md")
        
        # Load backend environments securely
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.ollama_endpoint = os.getenv("OLLAMA_HOST", "http://192.168.1.150:11434/api/chat")

    def _log_audit_trail(self, backend, prompt, response):
        """Enforces the strict V3 markdown audit trail rule."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = (
            f"\n\n## {timestamp} — Cognitive Audit Log\n"
            f"**Cognitive Hemisphere:** {backend}\n"
            f"**Query Telemetry:** *{prompt}*\n"
            f"**Brain Response:** {response}\n"
            f"\n---"
        )
        try:
            with open(self.journal_path, "a") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"[COGNITION] Failed to commit audit trail: {e}")

    def think(self, prompt, state="ALONE"):
        """Routes prompt based on the state machine constraint layer."""
        
        # ROUTE 1: Cloud Executive Brain (ENGAGED state or specialized requests)
        if state == "ENGAGED" and self.gemini_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=15)
                if res.status_code == 200:
                    output = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                    self._log_audit_trail("Cloud (Gemini 1.5 Flash)", prompt, output)
                    return output
            except Exception as e:
                print(f"[COGNITION] Cloud link timeout or fault: {e}")

        # ROUTE 2: Local Reflexive Brain Fallback (ALONE state background mapping)
        try:
            payload = {
                "model": "hermes3:latest",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }
            res = requests.post(self.ollama_endpoint, json=payload, timeout=20)
            if res.status_code == 200:
                output = res.json()["message"]["content"].strip()
                self._log_audit_trail("Local Workstation (Hermes 3)", prompt, output)
                return output
        except Exception as e:
            print(f"[COGNITION] Local network inference fault: {e}")
            
        return "Cognitive transmission array dropped frame sync."