from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class MLCodeSmellDetector:
    """ML-based code smell detection using CodeBERT."""
    
    _instance = None
    _model = None
    _tokenizer = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, model_name: str = "microsoft/codebert-base"):
        """Initialize the code smell detector."""
        if self._initialized:
            return
            
        self.model_name = model_name
        self.smell_types = [
            "long_method",
            "large_class",
            "duplicate_code",
            "dead_code",
            "complex_conditional"
        ]
        self._initialized = True
        
    def _ensure_model_loaded(self):
        """Lazy load the model and tokenizer."""
        global AutoTokenizer, AutoModelForSequenceClassification, torch
        
        if self._model is None:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            from config.settings import settings
            
            # Check if cache is enabled
            if settings.ML_MODEL_CACHE_ENABLED:
                logger.info("loading CodeBERT model (cached)...")
            else:
                logger.warning("ML Model caching disabled, but using singleton anyway for session")
                
            logger.info(f"Loading CodeBERT model: {self.model_name}")
            try:
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name,
                    num_labels=5  # Different types of code smells
                )
                
                # Move to configured device if available
                if settings.ML_DEVICE != "auto":
                    device = torch.device(settings.ML_DEVICE)
                    self._model.to(device)
                    
                logger.info("CodeBERT model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load ML model: {e}")
                raise

    @property
    def model(self):
        self._ensure_model_loaded()
        return self._model

    @property
    def tokenizer(self):
        self._ensure_model_loaded()
        return self._tokenizer
    
    def detect_smells(self, code: str) -> List[Dict]:
        """Detect code smells using ML model."""
        # Ensure loaded (redundant but safe if accessing properties directly)
        self._ensure_model_loaded()
        
        # Imports needed for this scope if not global
        import torch
        
        # Tokenize
        inputs = self.tokenizer(
            code,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )
        
        # Move inputs to device if model is on device
        if hasattr(self.model, "device"):
             inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # Extract smells with high confidence
        smells = []
        # cpu() call needed if tensor is on gpu
        probs = predictions[0].cpu().numpy() if predictions[0].is_cuda else predictions[0].numpy()
        
        for i, (smell_type, confidence) in enumerate(zip(self.smell_types, probs)):
            if confidence > 0.6:  # Threshold
                smells.append({
                    "type": smell_type,
                    "confidence": float(confidence),
                    "severity": self._determine_severity(float(confidence))
                })
        
        return smells
    
    def _determine_severity(self, confidence: float) -> str:
        """Determine severity based on confidence."""
        if confidence > 0.9:
            return "high"
        elif confidence > 0.7:
            return "medium"
        else:
            return "low"