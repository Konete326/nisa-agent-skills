from datetime import datetime
from google import genai
import config

class GeminiAdvisor:
    FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest"]

    def __init__(self, api_key=None, model_id="gemini-2.5-flash"):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model_id = model_id
        self.client = None
        self._setup_client()

    def _setup_client(self):
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
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
            "Analyze the instruction and determine the optimal action. "
            f"User instruction: {user_instruction}"
        )

        candidate_models = [self.model_id] + [m for m in self.FALLBACK_MODELS if m != self.model_id]
        last_error = None

        for target_model in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=target_model,
                    contents=prompt
                )
                reasoning_text = response.text.strip() if response and response.text else "No output"
                self._log_reasoning(user_instruction, reasoning_text)
                return {
                    "success": True,
                    "reasoning": reasoning_text,
                    "action": "ai_reasoning",
                    "model_used": target_model,
                    "parameters": {"instruction": user_instruction}
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
        try:
            collection = config.get_collection("reasoning_history")
            collection.insert_one({
                "timestamp": datetime.utcnow().isoformat(),
                "agent": config.AGENT_NAME,
                "prompt": prompt,
                "response": response
            })
        except Exception:
            pass

gemini_advisor = GeminiAdvisor()
