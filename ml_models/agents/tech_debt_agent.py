from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
import os
import json
import logging

logger = logging.getLogger(__name__)

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import PydanticOutputParser
except ImportError:
    pass

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
    from modified code snippets using Google's Gemini models.
    """
    def __init__(self, google_api_key: Optional[str] = None, model_name: str = "gemini-2.0-pro-exp-02-05"):
        self.api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not set for TechDebtAgent")
            
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.api_key,
            temperature=0.1 # Keep it strictly analytical
        ) if self.api_key else None
        
        self.output_parser = PydanticOutputParser(pydantic_object=TechDebtAnalysis)

    async def analyze_debt_delta(self, ast_contexts: List[Dict], language: str) -> TechDebtAnalysis:
        if not self.llm:
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
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("user", "Language: {language}\n\nModified AST Contexts:\n{contexts}")
        ])

        chain = prompt | self.llm | self.output_parser

        try:
            contexts_str = json.dumps(ast_contexts, indent=2)
            result = await chain.ainvoke({
                "language": language,
                "contexts": contexts_str,
                "format_instructions": self.output_parser.get_format_instructions()
            })
            return result
        except Exception as e:
            logger.error(f"TechDebtAgent failed: {str(e)}")
            return TechDebtAnalysis(
                verdict="🔴 Review required", 
                total_debt_hours=0.0, 
                findings=[TechDebtFinding(
                    severity="Critical", 
                    concept="LLM Failure", 
                    message=f"Failed to generate tech debt: {str(e)}", 
                    remediation_hours=0.0
                )]
            )
