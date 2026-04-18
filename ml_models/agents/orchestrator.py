from typing import List, Literal, Optional, Dict, Any, TypedDict, Annotated
from pydantic import BaseModel, Field
import os
import operator

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None
try:
    from langchain_community.llms import HuggingFaceHub
except ImportError:
    HuggingFaceHub = None
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END

class Finding(BaseModel):
    category: str = Field(description="Category of the finding, e.g., 'Security', 'Performance', 'Architecture'")
    severity: Literal['🔴', '🟡', '🟣'] = Field(description="Severity: 🔴 for critical/high, 🟡 for medium/warning, 🟣 for low/info or good practices")
    message: str = Field(description="Description of the issue")
    line: int = Field(description="Line number related to the issue, use 0 if file-wide")
    suggestion: Optional[str] = Field(None, description="Explanation of how to fix it")
    suggested_fix_diff: Optional[str] = Field(None, description="Unified diff string of the suggested fix. Make sure it uses valid unified diff format without markdown fences")

class FinalReview(BaseModel):
    verdict: Literal['pass', 'warn', 'fail'] = Field(description="The final verdict for this pull request or file based on findings.")
    summary: str = Field(description="A concise summary of the overall code quality and critical issues.")
    findings: List[Finding] = Field(description="A list of code findings")

# Defined state for LangGraph
class GraphState(TypedDict):
    code: str
    language: str
    filename: str
    static_issues: List[Dict[str, Any]]
    security_findings: List[Finding]
    performance_findings: List[Finding]
    architecture_findings: List[Finding]
    final_review: Optional[FinalReview]


class PRReviewOrchestrator:
    def _log_timing(self, label: str, start: float, end: float):
        print(f"[PROFILE] {label}: {end - start:.2f} seconds")

    """
    Multi-Agent PR Review Orchestrator using LangGraph and LangChain.
    Supports both Google Gemini (if GOOGLE_API_KEY is set) and Hugging Face (if HUGGINGFACE_API_KEY is set).
    """
    def __init__(self, backend: str = None, model_name: str = None, huggingface_api_key: Optional[str] = None, google_api_key: Optional[str] = None):
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        self.huggingface_api_key = huggingface_api_key or os.getenv("HUGGINGFACE_API_KEY")
        self.backend = backend or ("google" if self.google_api_key else "huggingface")
        if self.backend == "google":
            if not self.google_api_key or not ChatGoogleGenerativeAI:
                raise RuntimeError("Google backend selected but GOOGLE_API_KEY or langchain_google_genai is not available.")
            self.llm = ChatGoogleGenerativeAI(
                model=model_name or "gemini-2.0-pro-exp-02-05",
                google_api_key=self.google_api_key,
                temperature=0.2
            )
        elif self.backend == "huggingface":
            if not self.huggingface_api_key or not HuggingFaceHub:
                raise RuntimeError("Hugging Face backend selected but HUGGINGFACE_API_KEY or langchain_community.llms.HuggingFaceHub is not available.")
            self.llm = HuggingFaceHub(
                repo_id=model_name or "HuggingFaceH4/zephyr-7b-beta",
                huggingfacehub_api_token=self.huggingface_api_key,
                model_kwargs={"temperature": 0.2, "max_new_tokens": 512, "top_p": 0.95}
            )
        else:
            raise RuntimeError(f"Unknown backend: {self.backend}")
        self.output_parser = PydanticOutputParser(pydantic_object=FinalReview)
        self.workflow = self._build_graph()

    def call_llm_with_timing(self, *args, **kwargs):
        import time
        start = time.time()
        result = self.llm(*args, **kwargs)
        end = time.time()
        self._log_timing("HuggingFace LLM call", start, end)
        return result

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(GraphState)
        
        # Add nodes
        workflow.add_node("security_audit", self.security_audit_node)
        workflow.add_node("performance_profiling", self.performance_profiling_node)
        workflow.add_node("architectural_consistency", self.architecture_node)
        workflow.add_node("synthesize_review", self.synthesize_node)
        
        # Parallel execution of the three reviews
        workflow.set_entry_point("security_audit")
        
        # In a more advanced setup these could be true parallel using parallel branches in langgraph
        # For simplicity and robust state management here, we chain them or run them sequentially 
        # before synthesizing. Let's do sequential for state building:
        workflow.add_edge("security_audit", "performance_profiling")
        workflow.add_edge("performance_profiling", "architectural_consistency")
        workflow.add_edge("architectural_consistency", "synthesize_review")
        workflow.add_edge("synthesize_review", END)
        
        return workflow.compile()

    def _run_sub_agent(self, role: str, focus: str, state: dict) -> List[Finding]:
        if not self.llm:
            return []
            
        system_prompt = f"""You are an elite code reviewer specializing in {role}. 
Your focus is ONLY on {focus}.
Analyze the provided code and generate strict findings.
Format your output as a JSON list of Finding objects."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "File: {filename}\nLanguage: {language}\n\nCode:\n```{language}\n{code}\n```\n\nStatic Issues Detected: {static_issues}\n\nProvide findings as a JSON array where each object has: \n- category (string)\n- severity ('🔴', '🟡', '🟣')\n- message (string)\n- line (integer)\n- suggestion (string)\n- suggested_fix_diff (string). Do not return markdown, only the raw JSON array.")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "filename": state["filename"],
                "language": state["language"],
                "code": state["code"],
                "static_issues": str(state["static_issues"])
            })
            
            # Simple manual JSON parse since it's a list
            # Handle both BaseMessage (ChatModels) and str (LLMs)
            if hasattr(response, "content"):
                content = response.content.strip()
            else:
                content = str(response).strip()
                
            if content.startswith("```json"):
                content = content[7:-3].strip()
            
            import json
            data = json.loads(content)
            findings = []
            for item in data:
                findings.append(Finding(**item))
            return findings
        except Exception as e:
            print(f"Error in {role} agent: {e}")
            return []

    def security_audit_node(self, state: GraphState) -> GraphState:
        findings = self._run_sub_agent(
            role="Security Audit",
            focus="Identifying vulnerabilities, injection flaws, secure coding practices, and improper data handling.",
            state=state
        )
        return {"security_findings": findings}

    def performance_profiling_node(self, state: GraphState) -> GraphState:
        findings = self._run_sub_agent(
            role="Performance Profiling",
            focus="Algorithmic efficiency, memory leaks, redundant operations, and optimal use of language features.",
            state=state
        )
        return {"performance_findings": findings}

    def architecture_node(self, state: GraphState) -> GraphState:
        findings = self._run_sub_agent(
            role="Architectural Consistency",
            focus="Design patterns, modularity, coupling, naming conventions, and domain-driven design alignment.",
            state=state
        )
        return {"architecture_findings": findings}

    def synthesize_node(self, state: GraphState) -> GraphState:
        all_findings = []
        if state.get("security_findings"): all_findings.extend(state["security_findings"])
        if state.get("performance_findings"): all_findings.extend(state["performance_findings"])
        if state.get("architecture_findings"): all_findings.extend(state["architecture_findings"])
        
        if not self.llm:
            return {"final_review": FinalReview(verdict="warn", summary="LLM Not Configured", findings=all_findings)}
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the final reviewer synthesizing sub-agent findings into a final report.\n{format_instructions}"),
            ("user", "Synthesize these findings into a final review for {filename}:\n\n{findings}")
        ])
        
        chain = prompt | self.llm | self.output_parser
        
        try:
            final_review = chain.invoke({
                "filename": state["filename"],
                "findings": str([f.model_dump() for f in all_findings]),
                "format_instructions": self.output_parser.get_format_instructions()
            })
            return {"final_review": final_review}
        except Exception as e:
            print(f"Synthesis failed: {e}")
            return {"final_review": FinalReview(verdict="warn", summary=f"Failed to synthesize: {e}", findings=all_findings)}

    async def review_code_async(self, code: str, language: str, filename: str, static_issues: List[Dict]) -> FinalReview:
        initial_state = GraphState(
            code=code,
            language=language,
            filename=filename,
            static_issues=static_issues,
            security_findings=[],
            performance_findings=[],
            architecture_findings=[],
            final_review=None
        )
        
        result = await self.workflow.ainvoke(initial_state)
        return result["final_review"]
