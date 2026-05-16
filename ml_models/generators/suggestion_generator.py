import logging
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings

logger = logging.getLogger(__name__)

class SuggestionGenerator:
    """
    Generates actionable code snippets and fixes based on analysis findings.
    Uses a specialized LLM prompt to ensure suggestions are concise and correct.
    """
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.2
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an elite software architect. Your goal is to provide precise, "
                "production-ready code fixes for detected issues. \n\n"
                "Constraints:\n"
                "1. Only provide the necessary code changes.\n"
                "2. Use Markdown code blocks with the language specified.\n"
                "3. Explain WHY the change is necessary in one sentence.\n"
                "4. Ensure the code adheres to the original project's style.\n"
                "5. If the fix is too complex for a snippet, provide a high-level architectural step."
            )),
            ("human", (
                "Finding: {finding_name}\n"
                "Severity: {severity}\n"
                "File: {file_path}\n"
                "Context:\n{code_context}\n\n"
                "Please provide a corrected version of the code snippet."
            ))
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

    async def generate_suggestion(self, finding: Dict[str, Any]) -> str:
        """
        Generates a code suggestion for a specific analysis finding.
        """
        try:
            suggestion = await self.chain.ainvoke({
                "finding_name": finding.get("rule_name", "General Issue"),
                "severity": finding.get("severity", "Medium"),
                "file_path": finding.get("file_path", "unknown"),
                "code_context": finding.get("context", "No context provided")
            })
            return suggestion
        except Exception as e:
            logger.error(f"Error generating suggestion for {finding.get('rule_name')}: {e}")
            return "Could not generate a specific code suggestion. Please review the finding manually."

    async def generate_batch_suggestions(self, findings: List[Dict[str, Any]]) -> List[str]:
        """
        Generates suggestions for multiple findings in parallel.
        """
        import asyncio
        tasks = [self.generate_suggestion(f) for f in findings]
        return await asyncio.gather(*tasks)
