import threading
import time
import json
from pathlib import Path
from google import genai
import config
from evolution.critic import system_critic
from evolution.mutator import code_mutator

class EvolutionScout:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.model_id = "gemini-3.6-flash"
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.active = False
        self.worker = None

    def start_cycle(self):
        if not self.active and self.client:
            self.active = True
            self.worker = threading.Thread(target=self._scout_loop, daemon=True)
            self.worker.start()

    def stop_cycle(self):
        self.active = False

    def _scout_loop(self):
        while self.active:
            prompts = system_critic.formulate_prompts()
            for prompt_str in prompts:
                if not self.active:
                    break
                self._handle_prompt(prompt_str)
            time.sleep(3600)

    def _handle_prompt(self, prompt_str):
        try:
            req_data = json.loads(prompt_str)
            system_instruction = (
                "You are an AI optimization agent. Rewrite the provided code to resolve the issue. "
                "CRITICAL RULES: NO COMMENTS (no #, no docstrings), strictly <= 120 lines. "
                "Output MUST be valid raw Python code ONLY. Do not use markdown backticks."
            )
            
            target_file = req_data.get("target_file")
            original_code = (Path(config.BASE_DIR) / target_file).read_text(encoding="utf-8")
            prompt = f"ISSUE: {req_data.get('issue')}\nGOAL: {req_data.get('optimization_goal')}\nCODE:\n{original_code}"
            
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[system_instruction, prompt]
            )
            
            improved_code = response.text.strip()
            if improved_code.startswith("```python"):
                improved_code = improved_code[9:]
            if improved_code.endswith("```"):
                improved_code = improved_code[:-3]
            improved_code = improved_code.strip()
            
            code_mutator.stage_mutation(target_file, improved_code)
        except Exception:
            pass

evolution_scout = EvolutionScout()
