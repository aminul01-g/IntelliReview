from typing import List, Dict, Optional
import os
try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

# Optional imports for legacy providers
try:
    import openai
except ImportError:
    openai = None
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

class SuggestionGenerator:
    """Generate AI-powered code suggestions using LLMs."""
    
    def __init__(self, provider: str = "huggingface", api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize suggestion generator.
        
        Args:
            provider: 'huggingface', 'openai', or 'anthropic'
            api_key: API key for the provider
            model: Optional model identifier
        """
        self.provider = provider
        
        if provider == "huggingface":
            if not InferenceClient:
                raise ImportError("huggingface_hub is required for Hugging Face provider")
            self.api_key = api_key or os.getenv('HUGGINGFACE_API_KEY')
            self.model = model or os.getenv('HUGGINGFACE_MODEL', "deepseek-ai/DeepSeek-R1")
            self.client = InferenceClient(token=self.api_key)
            
        elif provider == "openai":
            if not openai:
                raise ImportError("openai is required for OpenAI provider")
            openai.api_key = api_key or os.getenv('OPENAI_API_KEY')
            self.model = model or "gpt-4"
            
        elif provider == "anthropic":
            if not Anthropic:
                raise ImportError("anthropic is required for Anthropic provider")
            self.client = Anthropic(api_key=api_key or os.getenv('ANTHROPIC_API_KEY'))
            self.model = model or "claude-3-sonnet-20240229"
            
        else:
            raise ValueError(f"Unknown provider: {provider}")
            
    @staticmethod
    def _strip_think_block(text: str) -> str:
        """Strip <think>...</think> reasoning blocks often produced by DeepSeek models."""
        import re
        return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    
    def generate_suggestion(
        self,
        code: str,
        issue: Dict,
        language: str = "python",
        context: Optional[str] = None
    ) -> Dict:
        """Generate a suggestion for a code issue."""
        
        prompt = self._build_prompt(code, issue, language, context)
        
        try:
            if self.provider == "huggingface":
                response = self._call_huggingface(prompt)
            elif self.provider == "openai":
                response = self._call_openai(prompt)
            else:
                response = self._call_anthropic(prompt)
            
            import json
            import re
            
            # Clean up the response to extract JSON
            clean_res = self._strip_think_block(response)
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
            clean_res = clean_res.strip()
            
            try:
                data = json.loads(clean_res)
                suggestion = f"**Problem:** {data.get('explanation', '')}\n\n**Fix:**\n```diff\n{data.get('diff', '')}\n```"
                confidence = float(data.get('confidence_score', 0.5))
            except json.JSONDecodeError:
                # Fallback if AI didn't return valid JSON
                suggestion = clean_res
                confidence = 0.5
            
            return {
                "suggestion": suggestion,
                "confidence": confidence,
                "issue_type": issue.get('type'),
                "severity": issue.get('severity')
            }
        
        except Exception as e:
            return {
                "suggestion": f"Error generating suggestion: {str(e)}",
                "confidence": 0.0,
                "issue_type": issue.get('type'),
                "severity": issue.get('severity')
            }
    
    def generate_refactoring_suggestion(
        self,
        code: str,
        language: str = "python"
    ) -> Dict:
        """Generate refactoring suggestions for code."""
        
        prompt = f"""Analyze the following {language} code and provide refactoring suggestions.
                    Focus on:
                    1. Code structure and organization
                    2. Design patterns that could be applied
                    3. Performance improvements
                    4. Readability enhancements

                    Code:
                    ```{language}
                        {code}
                    ```

                    Provide specific, actionable suggestions with code examples."""

        try:
            if self.provider == "huggingface":
                response = self._call_huggingface(prompt)
            elif self.provider == "openai":
                response = self._call_openai(prompt)
            else:
                response = self._call_anthropic(prompt)
            
            return {
                "refactoring_suggestions": response,
                "confidence": 0.8
            }
        
        except Exception as e:
            return {
                "refactoring_suggestions": f"Error: {str(e)}",
                "confidence": 0.0
            }
    
    def explain_code(self, code: str, language: str = "python") -> str:
        """Generate an explanation of what the code does."""
        
        prompt = f"""Explain what the following {language} code does in clear, concise language.
                    Focus on the main purpose, key logic, and any important details.

                    Code:
                    ```{language}
                        {code}
                    ```"""

        try:
            if self.provider == "huggingface":
                return self._call_huggingface(prompt)
            elif self.provider == "openai":
                return self._call_openai(prompt)
            else:
                return self._call_anthropic(prompt)
        
        except Exception as e:
            return f"Error generating explanation: {str(e)}"
    
    def _build_prompt(
        self,
        code: str,
        issue: Dict,
        language: str,
        context: Optional[str]
    ) -> str:
        """Build a concise, chunked prompt that guarantees JSON output."""
        
        issue_type = issue.get('type', 'unknown')
        severity = issue.get('severity', 'medium')
        message = issue.get('message', '')
        line = issue.get('line', 1)
        
        # --- Chunking Pipeline Hardening ---
        # Prevent context window overflow by chunking large files (max ~100 lines around issue)
        lines = code.split('\n')
        start_line = max(0, line - 50)
        end_line = min(len(lines), line + 50)
        code_chunk = "\n".join(lines[start_line:end_line])
        
        prompt = f"""You are an elite code reviewer mapping an AST-detected issue.

Issue: {issue_type} (severity: {severity})
Target Line (Original File L{line}): {message}

Chunked Source Code (Lines {start_line+1}-{end_line}):
```{language}
{code_chunk}
```

Respond ONLY with a valid JSON object matching exactly this structure. Do not wrap in markdown blocks, just raw JSON:
{{
  "explanation": "A concise 1-2 sentence plain-English explanation of why this line is a problem and what impact it has.",
  "diff": "A concise unified diff patch replacing the exact lines. E.g: -old\\n+new",
  "confidence_score": 0.95
}}

Ensure confidence_score is a float from 0.0 to 1.0 (Output 0 -> 0.4 for low, 0.5 -> 0.7 for medium, 0.8+ for high)."""

        if context:
            prompt += f"""\n\n--- CROSS-FILE PROJECT CONTEXT ---
{context}
--- END CONTEXT ---"""
        
        return prompt
    
    def _build_general_review_prompt(self, code: str, issues: List[Dict], language: str) -> str:
        """Build a prompt for an executive-level general code review."""
        
        # Summarize the detected issues for the AI
        issue_summary_lines = []
        for i, issue in enumerate(issues[:20], 1):  # Cap at 20 to avoid token overflow
            issue_summary_lines.append(
                f"  {i}. [{issue.get('severity', 'medium').upper()}] Line {issue.get('line', '?')}: "
                f"{issue.get('type', 'unknown')} — {issue.get('message', '')}"
            )
        issue_summary = "\n".join(issue_summary_lines) if issue_summary_lines else "  No issues detected."
        
        prompt = f"""You are a Principal Software Engineer conducting a formal code review.

Language: {language}
Total issues detected by static analysis: {len(issues)}

Detected issues:
{issue_summary}

Full source code:
```{language}
{code}
```

Write a professional **Executive Code Review** in Markdown using this structure:

## 🔍 Overview
One paragraph summarizing the code's purpose and overall quality.

## 📊 Issue Summary
| Category | Count | Severity |
|----------|-------|----------|
Group the detected issues into categories (Syntax, Logic, Security, Performance, Style) with counts.

## 🚨 Critical Findings
List the top 3 most important issues with brief explanations. If none are critical, state that.

## 🛡️ Security Assessment
One paragraph on security posture. Mention specific vulnerabilities if found.

## ⚡ Performance Notes
One paragraph on performance considerations.

## ✅ Recommendations
A numbered list of the top 5 actionable improvements, ordered by priority.

## 📝 Verdict
One sentence: is this code ready for production? Rate it: 🔴 Critical Issues / 🟡 Needs Work / 🟢 Good to Go.

Keep the entire review concise and professional (under 600 words)."""
        
        return prompt
    
    async def generate_general_review_async(self, code: str, issues: List[Dict], language: str) -> str:
        """Generate a single executive-level review of the entire codebase."""
        prompt = self._build_general_review_prompt(code, issues, language)
        
        try:
            if self.provider == "huggingface":
                response = await self._call_huggingface_async_long(prompt)
            elif self.provider == "openai":
                response = self._call_openai(prompt)
            else:
                response = self._call_anthropic(prompt)
            return self._strip_think_block(response)
        except Exception as e:
            return f"⚠️ AI Review unavailable: {str(e)}"
    
    def _build_project_review_prompt(self, file_manifest: List[Dict], project_summary: Dict) -> str:
        """Build a prompt for a holistic project-level architectural review."""
        
        # Build file tree representation
        file_tree_lines = []
        for f in file_manifest[:30]:  # Cap to fit token limit
            issues_str = f", {f['issue_count']} issues" if f.get('issue_count', 0) > 0 else ""
            file_tree_lines.append(
                f"  {f['file_path']} ({f['language']}, {f['lines']} lines{issues_str})"
            )
        file_tree = "\n".join(file_tree_lines)
        
        # Build per-file issue summary
        issue_details = []
        for f in file_manifest[:20]:
            if f.get('issue_count', 0) > 0:
                sev_str = ", ".join(f"{k}: {v}" for k, v in f.get('severity_counts', {}).items())
                top_issues = []
                for iss in f.get('issues', [])[:3]:
                    top_issues.append(f"    - L{iss.get('line', '?')}: [{iss.get('severity', '?')}] {iss.get('type', '?')} — {iss.get('message', '')}")
                issue_details.append(
                    f"  **{f['file_path']}** ({sev_str})\n" + "\n".join(top_issues)
                )
        issues_section = "\n".join(issue_details) if issue_details else "  No significant issues found across the project."
        
        # Build code snippets for the most critical files (first 500 chars each)
        code_snippets = []
        for f in file_manifest[:5]:
            if f.get('content'):
                snippet = f['content'][:800]
                related = f.get('related_files', [])
                related_str = f"  Related to: {', '.join(related)}" if related else ""
                code_snippets.append(f"### {f['file_path']}{related_str}\n```{f['language']}\n{snippet}\n```")
        code_section = "\n\n".join(code_snippets) if code_snippets else "Code snippets not available."
        
        # Build a cross-file dependency map
        dep_lines = []
        for f in file_manifest:
            related = f.get('related_files', [])
            if related:
                dep_lines.append(f"  {f['file_path']} ↔ {', '.join(related)}")
        dep_section = "\n".join(dep_lines) if dep_lines else "  No cross-file dependencies detected."
        
        prompt = f"""You are a Principal Software Architect conducting a comprehensive project audit.

## Project Overview
- Total files: {project_summary.get('total_files', 0)}
- Total lines of code: {project_summary.get('total_lines', 0)}
- Total issues detected: {project_summary.get('total_issues', 0)}
- Health score: {project_summary.get('health_score', 'N/A')}%
- Languages: {', '.join(f"{k} ({v} files)" for k, v in project_summary.get('language_breakdown', {}).items())}

## File Structure
{file_tree}

## Issue Summary by File
{issue_details}

## Key Source Code
{code_section}

## Cross-File Dependency Map
{dep_section}

---

Write a **Professional Project Audit Report** in Markdown using this structure:

## 🏗️ Architecture Overview
Analyze the project structure. Identify the architectural pattern (MVC, microservices, monolith, etc.), module organization, and separation of concerns. Note if the structure follows best practices for the detected language(s).

## 📁 Code Organization Assessment
- Is the file/folder structure logical and maintainable?
- Are there signs of code smell at the structural level (god files, circular dependencies, mixed concerns)?
- Recommendations for reorganization if needed.

## 🔍 Cross-File Analysis
Identify patterns that span multiple files:
- Repeated patterns or anti-patterns across files
- Inconsistent coding styles between files
- Shared vulnerabilities or systemic issues
- Common error handling patterns (or lack thereof)

## 🧪 Quality Metrics Interpretation
Interpret the static analysis results holistically:
- What does the health score of {project_summary.get('health_score', 'N/A')}% mean for this project?
- Are the issues concentrated in specific files or spread evenly?
- Which files need the most urgent attention?

## 🚀 Production Readiness Checklist
Rate each (✅ Ready / ⚠️ Needs Work / ❌ Missing):
- Error handling & graceful degradation
- Input validation & sanitization
- Security best practices
- Logging & monitoring readiness
- Configuration management
- Test coverage indicators
- Documentation quality

## 📋 Priority Action Items
A numbered list of the top 7 most impactful improvements, ordered by priority. For each item explain:
1. What to fix
2. Which file(s)
3. Why it matters

## 📊 Final Verdict
Rate the project overall:
- 🔴 **Not Production Ready** — Critical blockers exist
- 🟡 **Needs Significant Work** — Functional but risky
- 🟢 **Production Ready** — Minor improvements only

One paragraph final assessment.

Keep the entire review under 800 words. Be specific, cite file names and line numbers where possible."""
        
        return prompt
    
    async def generate_project_review_async(self, file_manifest: List[Dict], project_summary: Dict) -> str:
        """Generate a holistic project-level architectural review."""
        prompt = self._build_project_review_prompt(file_manifest, project_summary)
        
        try:
            if self.provider == "huggingface":
                response = await self._call_huggingface_async_long(prompt)
            elif self.provider == "openai":
                response = self._call_openai(prompt)
            else:
                response = self._call_anthropic(prompt)
            return self._strip_think_block(response)
        except Exception as e:
            return f"⚠️ Project AI Review unavailable: {str(e)}"
    
    async def generate_suggestion_async(
        self,
        code: str,
        issue: Dict,
        language: str = "python",
        context: Optional[str] = None
    ) -> Dict:
        """Generate a suggestion for a code issue asynchronously."""
        
        prompt = self._build_prompt(code, issue, language, context)
        
        try:
            if self.provider == "huggingface":
                response = await self._call_huggingface_async(prompt)
            else:
                # Fallback to sync for now or implement others if needed
                # To prevent endless loop, use direct sync call 
                # (Note: we just fallback to returning raw text in extreme cases)
                response = "Fallback syncing not async compatible here."
            
            import json
            import re
            
            clean_res = self._strip_think_block(response)
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
            clean_res = clean_res.strip()
            
            try:
                data = json.loads(clean_res)
                suggestion = f"**Problem:** {data.get('explanation', '')}\n\n**Fix:**\n```diff\n{data.get('diff', '')}\n```"
                confidence = float(data.get('confidence_score', 0.5))
            except json.JSONDecodeError:
                suggestion = clean_res
                confidence = 0.5
            
            return {
                "suggestion": suggestion,
                "confidence": confidence,
                "issue_type": issue.get('type'),
                "severity": issue.get('severity')
            }
        
        except Exception as e:
            return {
                "suggestion": f"Error generating suggestion: {str(e)}",
                "confidence": 0.0,
                "issue_type": issue.get('type'),
                "severity": issue.get('severity')
            }

    async def generate_project_plan_async(
        self,
        config_files_content: str,
        directory_tree: str
    ) -> str:
        """Generate a logic-first architectural plan.md based on project configs and tree."""
        prompt = f"""You are an elite Software Architecture Reviewer. Your first task in reviewing a new project is to build a "plan.md" that maps the holistic understanding of the project.

Here is the directory tree of the project:
{directory_tree}

Here are the contents of the core configuration files (e.g. package.json, requirements.txt, README.md):
{config_files_content}

Write a comprehensive `plan.md` document that:
1. Identifies the core purpose and assumed architecture (e.g. MVC, Microservices, Serverless).
2. Maps out the critical data flows and primary tech stack priorities.
3. Defines the exact "Review Workflow" — which core logic files must be prioritized to identify logical debt.

Output ONLY the markdown content for plan.md."""
        
        try:
            if self.provider == "huggingface":
                return await self._call_huggingface_async_long(prompt)
            else:
                return self._call_openai(prompt)
        except Exception as e:
            return f"# IntelliReview Default Plan\nFailed to generate project plan from LLM: {str(e)}"

    async def generate_auto_fix_async(
        self,
        code: str,
        issues: List[Dict],
        language: str = "python",
        filename: str = "file",
        plan_md: Optional[str] = None
    ) -> Dict:
        """Generate a unified diff patch that auto-fixes the top issues in the code."""
        
        # Summarize top issues for the prompt
        issue_lines = []
        for i, issue in enumerate(issues[:5], 1):
            issue_lines.append(
                f"  {i}. Line {issue.get('line', '?')}: [{issue.get('severity', 'medium')}] "
                f"{issue.get('type', '?')} — {issue.get('message', '')}"
            )
        issue_summary = "\n".join(issue_lines) if issue_lines else "  No issues."
        
        prompt = f"""You are an expert software engineer. Fix the following issues in this {language} code.

File: {filename}
Issues to fix:
{issue_summary}

Original code:
```{language}
{code}
```"""

        if plan_md:
            prompt += f"""\n
--- PROJECT ARCHITECTURE PLAN (plan.md) ---
{plan_md}
----------------------------------------
CRITICAL INSTRUCTION: Ensure your fix is validated against the architectural plan above. Do not break core data flows, architectural invariants, or the project's logic intent just to fix a local syntax error.
"""

        prompt += f"""\n
Respond with ONLY a unified diff patch in this exact format (no explanation, no markdown fences around the diff):

--- a/{filename}
+++ b/{filename}
@@ -LINE,COUNT +LINE,COUNT @@
-old line
+new fixed line

Rules:
- Fix ONLY the listed issues. Do not refactor unrelated code.
- Validate your fix logic against the project plan if provided.
- Keep the diff minimal — change only the lines that need fixing.
- If an issue cannot be auto-fixed safely without violating architecture, skip it.
- Output ONLY the diff, nothing else."""
        
        try:
            if self.provider == "huggingface":
                response = await self._call_huggingface_async_long(prompt)
            elif self.provider == "openai":
                response = self._call_openai(prompt)
            else:
                response = self._call_anthropic(prompt)
            
            return {
                "filename": filename,
                "diff": self._strip_think_block(response),
                "issues_addressed": len(issues[:5]),
                "status": "generated"
            }
        except Exception as e:
            return {
                "filename": filename,
                "diff": None,
                "issues_addressed": 0,
                "status": f"failed: {str(e)}"
            }

    def _call_huggingface(self, prompt: str) -> str:
        """Call Hugging Face Inference API."""
        import requests
        # Using the new router endpoint with model in payload
        url = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.3
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise Exception(f"Hugging Face API error (router failed): {str(e)}")

    async def _call_huggingface_async(self, prompt: str) -> str:
        """Call Hugging Face Inference API asynchronously (short responses)."""
        import httpx
        url = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.3
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                raise Exception(f"Hugging Face Async API error: {str(e)}")

    async def _call_huggingface_async_long(self, prompt: str) -> str:
        """Call Hugging Face Inference API asynchronously (long responses for general review)."""
        import httpx
        url = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500,
            "temperature": 0.3
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=90.0)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                raise Exception(f"Hugging Face Async API error (long): {str(e)}")

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert code reviewer and software engineer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text.strip()
    