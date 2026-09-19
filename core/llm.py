import os
import json
import re
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"

AVAILABLE_MODELS = {
    "Llama 3.3 70B (Recommended)": "meta-llama/llama-3.3-70b-instruct",
    "DeepSeek R1 Distill 70B": "deepseek/deepseek-r1-distill-llama-70b",
    "Qwen 2.5 Coder 32B": "qwen/qwen-2.5-coder-32b-instruct",
    "Llama 3.1 8B (Fast)": "meta-llama/llama-3.1-8b-instruct"
}

class LLMClient:
    """
    OpenRouter API Client wrapper for Open-Source LLMs using OpenAI SDK.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": "https://github.com/datachat-fde",
                    "X-Title": "DataChat Darwinbox FDE App"
                }
            )

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def generate_completion(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        model: Optional[str] = None,
        temperature: float = 0.1
    ) -> str:
        """
        Generates text completion from OpenRouter LLM.
        """
        if not self.is_configured():
            raise ValueError("OpenRouter API Key is missing. Please provide your key in .env or the UI sidebar.")

        target_model = model or self.model

        response = self.client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=2048
        )
        return response.choices[0].message.content.strip()

    def generate_json(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates completion and safely parses structured JSON output.
        """
        system_with_json_instruction = system_prompt + "\nIMPORTANT: Respond ONLY with valid raw JSON object. Do not include markdown code block backticks ``` or explanatory text."
        
        raw_output = self.generate_completion(
            system_prompt=system_with_json_instruction,
            user_prompt=user_prompt,
            model=model,
            temperature=0.0
        )
        
        # Clean markdown formatting if present
        clean_output = re.sub(r"^```(?:json)?\s*", "", raw_output, flags=re.IGNORECASE)
        clean_output = re.sub(r"\s*```$", "", clean_output).strip()
        
        try:
            return json.loads(clean_output)
        except json.JSONDecodeError as e:
            # Fallback regex extraction if model included leading/trailing prose
            match = re.search(r"(\{.*\})", clean_output, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse LLM JSON response: {raw_output}") from e
