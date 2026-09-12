from datetime import datetime
import json
import threading
from google import genai
from google.genai import types
import config

class GeminiAdvisor:
    FALLBACK_MODELS = ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3.5-flash", "gemini-3.6-flash"]

    def __init__(self, api_key=None, model_id="gemini-flash-latest"):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model_id = model_id
        self.client = None
        self._setup_client()

    def _setup_client(self):
        if self.api_key:
            try:
                opts = types.HttpOptions(timeout=4000, headers={"X-Server-Timeout": "10"})
                self.client = genai.Client(api_key=self.api_key, http_options=opts)
            except Exception:
                self.client = None

    def plan_task(self, user_instruction):
        if not self.client:
            return {
                "success": False,
                "reasoning": "Gemini API client not configured. Set GEMINI_API_KEY.",
                "action": "offline_response",
                "parameters": {"input": user_instruction}
            }

        prompt = (
            "You are Nisa, an autonomous native Windows desktop operator. "
            "Analyze the instruction (English, Urdu, Roman Urdu) and determine the intent. "
            "Output strictly valid JSON with no markdown. "
            "If simple app launch: {\"intent\": \"launch_app\", \"target\": \"notepad\"}. "
            "If multi-step instruction: {\"intent\": \"execute_skill\", \"target\": \"notepad\", \"steps\": [{\"action\": \"focus_or_launch\"}, {\"action\": \"write\", \"text\": \"...\"}, {\"action\": \"save\", \"path\": \"default\"}]}. "
            f"Instruction: {user_instruction}"
        )

        candidate_models = self.FALLBACK_MODELS
        last_error = None

        for target_model in candidate_models:
            try:
                cfg = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
                response = self.client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=cfg
                )
                raw_text = response.text.strip() if response and response.text else "{}"
                self._log_reasoning(user_instruction, raw_text)
                try:
                    parsed = json.loads(raw_text)
                except Exception:
                    parsed = {"intent": "ai_reasoning", "parameters": {"raw": raw_text}}

                return {
                    "success": True,
                    "reasoning": raw_text,
                    "action": parsed.get("intent", "ai_reasoning"),
                    "target": parsed.get("target", parsed.get("parameters", {}).get("target", "")),
                    "steps": parsed.get("steps", []),
                    "model_used": target_model,
                    "parameters": parsed.get("parameters", {})
                }
            except Exception as api_error:
                last_error = api_error

        return {
            "success": False,
            "reasoning": f"Gemini API failure across candidate models: {str(last_error)}",
            "action": "error",
            "parameters": {}
        }

    def _log_reasoning(self, prompt, response):
        def _write():
            try:
                config.get_collection("reasoning_history").insert_one({
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent": config.AGENT_NAME,
                    "prompt": prompt,
                    "response": response
                })
            except Exception: pass
        threading.Thread(target=_write, daemon=True).start()

gemini_advisor = GeminiAdvisor()
