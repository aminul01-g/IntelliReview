from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
import os
import json
import logging

logger = logging.getLogger(__name__)

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    LANGCHAIN_GOOGLE_AVAILABLE = True
except ImportError:
    ChatGoogleGenerativeAI = None
    LANGCHAIN_GOOGLE_AVAILABLE = False

try:
    from langchain_huggingface import HuggingFaceEndpoint
    LANGCHAIN_HF_AVAILABLE = True
except ImportError:
    HuggingFaceEndpoint = None
    LANGCHAIN_HF_AVAILABLE = False

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import PydanticOutputParser
    LANGCHAIN_CORE_AVAILABLE = True
except ImportError:
    ChatPromptTemplate = None
    PydanticOutputParser = None
    LANGCHAIN_CORE_AVAILABLE = False

try:
    from huggingface_hub import InferenceClient
    HF_HUB_AVAILABLE = True
except ImportError:
    InferenceClient = None
    HF_HUB_AVAILABLE = False

class TechDebtFinding(BaseModel):
    severity: Literal['Critical', 'High', 'Medium', 'Low'] = Field(description="Severity classification matching MetricsView severity schema.")
    concept: str = Field(description="The architectural or code quality smell detected.")
    message: str = Field(description="Detailed explanation of the technical debt.")
    remediation_hours: float = Field(description="Estimated hours to fix this specific technical debt block.")

class TechDebtAnalysis(BaseModel):
    verdict: str = Field(description="Overall verdict string (e.g. '✅ Clean', '⚠️ Needs attention', '🔴 Review required')")
    total_debt_hours: float = Field(description="Total estimated hours of technical debt delta introduced.")
    findings: List[TechDebtFinding] = Field(description="List of specific tech debt findings.")

class TechDebtAgent:
    """
    LangChain agent dedicated to extracting and evaluating Technical Debt
    from modified code snippets using Google Gemini or HuggingFace models.
    """
    def __init__(self, backend: str = None, model_name: str = None, huggingface_api_key: Optional[str] = None, google_api_key: Optional[str] = None):
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        self.huggingface_api_key = huggingface_api_key or os.getenv("HUGGINGFACE_API_KEY")
        self.backend = backend or ("google" if self.google_api_key else "huggingface")
        self.model_name = model_name or ("gemini-2.0-pro-exp-02-05" if self.backend == "google" else "gpt2")
        
        self.llm = None
        self.hf_client = None
        
        if self.backend == "google":
            if not self.google_api_key or not LANGCHAIN_GOOGLE_AVAILABLE:
                logger.warning("Google backend selected but GOOGLE_API_KEY or langchain_google_genai is not available.")
            else:
                self.llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.google_api_key,
                    temperature=0.1 # Keep it strictly analytical
                )
        elif self.backend == "huggingface":
            if not self.huggingface_api_key:
                logger.warning("HuggingFace backend selected but HUGGINGFACE_API_KEY is not available.")
            elif LANGCHAIN_HF_AVAILABLE:
                self.llm = HuggingFaceEndpoint(
                    repo_id=self.model_name,
                    huggingfacehub_api_token=self.huggingface_api_key,
                    temperature=0.1,
                    max_new_tokens=1024,
                    top_p=0.95
                )
            elif HF_HUB_AVAILABLE:
                # Fallback to direct InferenceClient
                self.hf_client = InferenceClient(
                    model=self.model_name,
                    token=self.huggingface_api_key
                )
            else:
                logger.warning("HuggingFace backend selected but neither langchain_huggingface nor huggingface_hub is available.")
        
        if LANGCHAIN_CORE_AVAILABLE:
            self.output_parser = PydanticOutputParser(pydantic_object=TechDebtAnalysis)
        else:
            self.output_parser = None

    async def analyze_debt_delta(self, ast_contexts: List[Dict], language: str) -> TechDebtAnalysis:
        if not self.llm and not self.hf_client:
            return TechDebtAnalysis(verdict="⚠️ Error", total_debt_hours=0.0, findings=[])

        system_template = """
You are a Principal Software Architect specializing in measuring Technical Debt Deltas in Pull Requests.
Your responsibility is strictly to evaluate the provided code changes (AST Functions) and estimate technical debt introduced.

Evaluate for:
- Cyclomatic rot or complexity increases
- Duplication and architectural coupling
- Readability drops and missing abstractions

Output your response strictly according to the following JSON schema mapping exactly to the User Interface:
{format_instructions}
"""
        
        contexts_str = json.dumps(ast_contexts, indent=2)
        user_message = f"Language: {language}\n\nModified AST Contexts:\n{contexts_str}"
        
        if self.llm:
            # Use LangChain interface (Google or HuggingFace via LangChain)
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_template),
                ("user", user_message)
            ])

            chain = prompt | self.llm | self.output_parser

            try:
                result = await chain.ainvoke({
                    "language": language,
                    "contexts": contexts_str,
                    "format_instructions": self.output_parser.get_format_instructions()
                })
                return result
            except Exception as e:
                logger.error(f"TechDebtAgent LangChain failed: {str(e)}")
                return TechDebtAnalysis(
                    verdict="🔴 Review required",
                    total_debt_hours=0.0,
                    findings=[]
                )
        elif self.hf_client:
            # Use direct HuggingFace InferenceClient
            try:
                full_prompt = f"{system_template.format(format_instructions=self.output_parser.get_format_instructions())}\n\n{user_message}"
                
                response = self.hf_client.text_generation(
                    full_prompt,
                    model=self.model_name,
                    max_new_tokens=1024,
                    temperature=0.1,
                    top_p=0.95
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
                
                # Try to parse the JSON response
                try:
                    result_dict = json.loads(response)
                    return TechDebtAnalysis(**result_dict)
                except Exception as parse_e:
                    logger.warning(f"Failed to parse HuggingFace response: {parse_e}, response: {response}")
                
                # Fallback if parsing fails
                return TechDebtAnalysis(
                    verdict="⚠️ Analysis completed (parsing issues)",
                    total_debt_hours=0.0,
                    findings=[]
                )
            except Exception as e:
                logger.error(f"TechDebtAgent HuggingFace failed: {str(e)}")
                return TechDebtAnalysis(
                    verdict="🔴 Review required",
                    total_debt_hours=0.0,
                    findings=[]
                )
        else:
            return TechDebtAnalysis(verdict="⚠️ Error", total_debt_hours=0.0, findings=[])
