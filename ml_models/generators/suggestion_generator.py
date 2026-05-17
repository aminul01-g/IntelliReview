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
        # Use HUGGINGFACE_MODEL as fallback since LLM_MODEL doesn't exist
        model = getattr(settings, 'LLM_MODEL', settings.HUGGINGFACE_MODEL)
        api_key = getattr(settings, 'GOOGLE_API_KEY', None)

        if api_key:
            self.llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=0.2
            )
        else:
            # Fallback - will need HuggingFace API or mock
            self.llm = None
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

        # Only create chain if LLM is available
        if self.llm:
            self.chain = self.prompt | self.llm | StrOutputParser()
        else:
            self.chain = None

    async def generate_suggestion(self, finding: Dict[str, Any]) -> str:
        """
        Generates a code suggestion for a specific analysis finding.
        """
        return await self.generate_suggestion_async(finding)

    async def generate_suggestion_async(self, code: str, finding: Dict[str, Any], language: str = "python") -> Dict[str, Any]:
        """
        Async version for generating suggestions with code context.
        """
        if not self.chain:
            return {"suggestion": "Suggestion generation not available - no LLM configured."}

        try:
            suggestion = await self.chain.ainvoke({
                "finding_name": finding.get("type", "Code Issue"),
                "severity": finding.get("severity", "Medium"),
                "file_path": "code snippet",
                "code_context": code[:500] if code else "No context"
            })
            return {"suggestion": suggestion}
        except Exception as e:
            logger.error(f"Error generating suggestion: {e}")
            return {"suggestion": "Could not generate suggestion."}

    async def generate_general_review_async(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Generate a general AI overview/review of the code.
        """
        if not self.chain:
            return {"overview": "AI review not available - no LLM configured."}

        try:
            review_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a senior code reviewer. Provide a brief overview of the code quality and potential issues."),
                ("human", "Review this {language} code:\n{code}")
            ])
            review_chain = review_prompt | self.llm | StrOutputParser()
            overview = await review_chain.ainvoke({"language": language, "code": code[:1000]})
            return {"overview": overview}
        except Exception as e:
            logger.error(f"Error generating review: {e}")
            return {"overview": "Could not generate review."}

    async def generate_batch_suggestions(self, findings: List[Dict[str, Any]]) -> List[str]:
        """
        Generates suggestions for multiple findings in parallel.
        """
        import asyncio
        tasks = [self.generate_suggestion(f) for f in findings]
        return await asyncio.gather(*tasks)
