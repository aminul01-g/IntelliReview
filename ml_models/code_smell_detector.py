from typing import List, Dict
import logging
import os
import json

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

logger = logging.getLogger(__name__)

class MLCodeSmellDetector:
    """ML-based code smell detection using generative LLMs."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, model_name: str = "deepseek-ai/DeepSeek-R1", api_key: str = None):
        """Initialize the code smell detector to use Hugging Face Inference."""
        if self._initialized:
            return
            
        self.model_name = os.getenv('HUGGINGFACE_SMELL_MODEL', model_name)
        self.api_key = api_key or os.getenv('HUGGINGFACE_API_KEY')
        
        if not InferenceClient:
            logger.warning("huggingface_hub not installed. Code smell detection will fail playfully.")
            self.client = None
        else:
            self.client = InferenceClient(token=self.api_key)
            
        self.smell_types = [
            "long_method",
            "large_class",
            "duplicate_code",
            "dead_code",
            "complex_conditional"
        ]
        self._initialized = True
        
    def detect_smells(self, code: str) -> List[Dict]:
        """Detect code smells using the Generative LLM Prompts."""
        if not self.client:
            return []
            
        prompt = f"""You are a static code analyzer identifying anti-patterns.
Review the following code and detect if it has any of these code smells: {', '.join(self.smell_types)}

Code:
```
{code}
```

Output ONLY a raw JSON array of objects, with no markdown fences, representing the smells found. 
Format: [{{"type": "long_method", "confidence": 0.85, "severity": "high"}}]
If no smells are found, output []."""

        try:
            response = self.client.text_generation(
                prompt,
                model=self.model_name,
                max_new_tokens=256,
                temperature=0.1
            )
            
            # Clean up the response to extract JSON
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            smells = json.loads(response)
            if isinstance(smells, list):
                return smells
            return []
        except Exception as e:
            logger.error(f"Code smell generation failed: {e}")
            return []