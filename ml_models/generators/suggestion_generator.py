import logging
from typing import Any, Dict, List, Optional
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
    def __init__(self, provider: str = "huggingface", **kwargs):
        self.provider = provider
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
            self.llm: Optional[ChatGoogleGenerativeAI] = None
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
            self.chain: Optional[Any] = None

    async def generate_suggestion(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a code suggestion for a specific analysis finding.

        Returns a dict with a "suggestion" key whose value is always a **string**.
        """
        result = await self.generate_suggestion_async(code="", finding=finding)
        # Defensive: ensure the 'suggestion' value is a plain string so
        # downstream Pydantic models (Issue.suggestion) never receive a dict.
        if isinstance(result, dict):
            suggestion = result.get("suggestion", "")
            if isinstance(suggestion, dict):
                suggestion = suggestion.get("overview") or suggestion.get("suggestion") or str(suggestion)
            result["suggestion"] = str(suggestion) if suggestion else ""
        return result

    async def generate_suggestion_async(self, code: str, finding: Dict[str, Any], language: str = "python") -> Dict[str, Any]:
        """
        Async version for generating suggestions with code context.

        Always returns ``{"suggestion": "<plain string>"}``.
        """
        if not self.chain:
            # Fallback: return a dict with a **string** value (not a nested dict)
            return {"suggestion": "Suggestion generation not available - no LLM configured."}

        try:
            suggestion = await self.chain.ainvoke({
                "finding_name": finding.get("type", "Code Issue"),
                "severity": finding.get("severity", "Medium"),
                "file_path": "code snippet",
                "code_context": code[:500] if code else "No context"
            })
            # Ensure we always return a string
            if isinstance(suggestion, dict):
                suggestion = suggestion.get("overview") or suggestion.get("suggestion") or str(suggestion)
            return {"suggestion": str(suggestion)}
        except Exception as e:
            logger.error(f"Error generating suggestion: {e}")
            return {"suggestion": "Could not generate suggestion."}

    async def generate_general_review_async(self, code: str, issues: Any = None, language: str = "python") -> str:
        """
        Generate a general AI overview/review of the code.

        Returns a plain string (not a dict) so it can be assigned directly
        to Issue.suggestion without causing Pydantic validation errors.

        Args:
            code: The source code to review.
            issues: Optional list of detected issues to include as context.
            language: Programming language of the code.
        """
        if not self.chain:
            return "AI review not available - no LLM configured."

        try:
            issues_context = ""
            if issues and isinstance(issues, list):
                top_issues = issues[:10]
                issues_context = "\nDetected issues:\n" + "\n".join(
                    f"- [{i.get('severity','info')}] {i.get('type','')}: {i.get('message','')}"
                    for i in top_issues
                )

            review_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a senior code reviewer. Provide a brief overview of the code quality and potential issues."),
                ("human", "Review this {language} code:\n{code}{issues_context}")
            ])
            review_chain = review_prompt | self.llm | StrOutputParser()
            overview = await review_chain.ainvoke({"language": language, "code": code[:1000], "issues_context": issues_context})
            return overview
        except Exception as e:
            logger.error(f"Error generating review: {e}")
            return "Could not generate review."

    async def generate_batch_suggestions(self, findings: List[Dict[str, Any]]) -> List[str]:
        """
        Generates suggestions for multiple findings in parallel.
        """
        import asyncio
        tasks = [self.generate_suggestion(f) for f in findings]
        return await asyncio.gather(*tasks)

    async def generate_project_plan_async(
        self, config_files_content: str = "", directory_tree: str = ""
    ) -> str:
        """
        Generate a strategic analysis plan for an uploaded project.
        """
        if not self.llm:
            return "# IntelliReview Plan\nAI plan generation not available - no LLM configured."

        try:
            plan_prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "You are an elite software architect. Generate a concise Markdown analysis plan "
                 "for the project described below. Include key areas to review and potential risks."),
                ("human",
                 "Project config files:\n{config_files}\n\nDirectory tree:\n{directory_tree}\n\n"
                 "Generate an analysis plan.")
            ])
            plan_chain = plan_prompt | self.llm | StrOutputParser()
            return await plan_chain.ainvoke({
                "config_files": config_files_content[:3000],
                "directory_tree": directory_tree[:3000],
            })
        except Exception as e:
            logger.error(f"Error generating project plan: {e}")
            return f"# IntelliReview Plan\nError generating plan: {e}"

    async def generate_project_review_async(
        self, file_manifest: List[Dict[str, Any]], project_summary: Dict[str, Any]
    ) -> str:
        """
        Generate an AI architectural review for the entire project.
        """
        if not self.llm:
            return "AI architectural review not available - no LLM configured."

        try:
            # Build a compact summary of each file
            file_summaries = []
            for entry in file_manifest[:15]:
                file_summaries.append(
                    f"- {entry.get('file_path', 'unknown')} ({entry.get('language', '?')}, "
                    f"{entry.get('issue_count', 0)} issues, severity: {entry.get('severity_counts', {})})"
                )
            files_text = "\n".join(file_summaries)

            review_prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "You are an elite software architect reviewing a full project. "
                 "Provide a concise Markdown architectural review covering code quality, "
                 "patterns, risks, and actionable recommendations."),
                ("human",
                 "Project summary:\n{project_summary}\n\nFile manifest:\n{files_text}\n\n"
                 "Provide your architectural review.")
            ])
            review_chain = review_prompt | self.llm | StrOutputParser()
            import json as _json
            return await review_chain.ainvoke({
                "project_summary": _json.dumps(project_summary, default=str),
                "files_text": files_text,
            })
        except Exception as e:
            logger.error(f"Error generating project review: {e}")
            return f"AI architectural review failed: {e}"

    async def generate_auto_fix_async(
        self,
        code: str,
        issues: List[Dict[str, Any]],
        language: str = "python",
        filename: str = "unknown",
        plan_md: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a unified diff auto-fix patch for files with critical/high issues.
        """
        if not self.llm:
            return {"diff": None, "reason": "No LLM configured"}

        try:
            critical_issues = [i for i in issues if i.get("severity") in ("critical", "high")][:5]
            if not critical_issues:
                return {"diff": None, "reason": "No critical/high issues"}

            issues_text = "\n".join(
                f"- L{i.get('line', '?')} [{i.get('severity')}] {i.get('type', '')}: {i.get('message', '')}"
                for i in critical_issues
            )

            fix_prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "You are an auto-fix engine. Given source code and a list of critical issues, "
                 "produce a minimal unified diff that fixes ONLY the listed issues. "
                 "Output ONLY the diff, no explanation."),
                ("human",
                 "File: {filename} ({language})\n\nIssues:\n{issues_text}\n\n"
                 "Code:\n```\n{code}\n```\n\nGenerate the unified diff fix.")
            ])
            fix_chain = fix_prompt | self.llm | StrOutputParser()
            diff = await fix_chain.ainvoke({
                "filename": filename,
                "language": language,
                "issues_text": issues_text,
                "code": code[:4000],
            })
            return {"diff": diff, "filename": filename, "issues_fixed": len(critical_issues)}
        except Exception as e:
            logger.error(f"Error generating auto-fix: {e}")
            return {"diff": None, "reason": str(e)}

    async def generate_architectural_hypothesis(
        self, problem_statement: str, context_code: str = ""
    ) -> str:
        """
        AI-powered hypothesis generation for complex architectural issues.
        Accepts a problem description and suggests possible structural changes.

        Returns a plain string with the hypothesis.
        """
        if not self.llm:
            return (
                "Architectural hypothesis generation not available - no LLM configured. "
                "Please review the problem statement manually and consider applying "
                "standard design patterns (Strategy, Facade, Repository) to decouple concerns."
            )

        try:
            hypothesis_prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "You are an elite software architect. Given a problem statement and optional "
                 "code context, generate a concise architectural hypothesis describing the root "
                 "cause and a concrete refactoring strategy to resolve it. Use Markdown."),
                ("human",
                 "Problem statement:\n{problem_statement}\n\n"
                 "Code context:\n{context_code}\n\n"
                 "Provide your architectural hypothesis and suggested fix.")
            ])
            hypothesis_chain = hypothesis_prompt | self.llm | StrOutputParser()
            return await hypothesis_chain.ainvoke({
                "problem_statement": problem_statement[:2000],
                "context_code": context_code[:3000] if context_code else "No code context provided.",
            })
        except Exception as e:
            logger.error(f"Error generating architectural hypothesis: {e}")
            return f"Hypothesis generation failed: {e}. Please review the problem manually."
