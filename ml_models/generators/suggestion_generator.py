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
            self.model = model or os.getenv('HUGGINGFACE_MODEL', "Qwen/Qwen2.5-Coder-7B-Instruct")
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
            
            return {
                "suggestion": response,
                "confidence": self._estimate_confidence(response),
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
        """Build a concise per-issue prompt that returns only a short fix."""
        
        issue_type = issue.get('type', 'unknown')
        severity = issue.get('severity', 'medium')
        message = issue.get('message', '')
        line = issue.get('line', 0)
        
        prompt = f"""You are an expert code reviewer. A static analyzer found the following issue in {language} code.

Issue: {issue_type} (severity: {severity})
Line {line}: {message}

Source code:
```{language}
{code}
```

Provide a concise response in this EXACT format (no extra sections):

**Problem:** One sentence explaining what is wrong and why.

**Fix:**
```{language}
// corrected code snippet for the affected line(s) only
```

**Impact:** One sentence on what could happen if this is not fixed.

Keep your entire response under 150 words. Do NOT repeat the full file. Only show the affected line(s)."""

        if context:
            prompt += f"""\n\n--- CROSS-FILE PROJECT CONTEXT ---
The following related files exist in the same project. Use them to understand
how this file connects to the broader codebase and catch cross-file issues
(e.g., mismatched function signatures, broken imports, schema drift):

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
            return response
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
            return response
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
                response = self.generate_suggestion(code, issue, language, context)["suggestion"]
            
            return {
                "suggestion": response,
                "confidence": self._estimate_confidence(response),
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

    async def generate_auto_fix_async(
        self,
        code: str,
        issues: List[Dict],
        language: str = "python",
        filename: str = "file"
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
```

Respond with ONLY a unified diff patch in this exact format (no explanation, no markdown fences around the diff):

--- a/{filename}
+++ b/{filename}
@@ -LINE,COUNT +LINE,COUNT @@
-old line
+new fixed line

Rules:
- Fix ONLY the listed issues. Do not refactor unrelated code.
- Keep the diff minimal — change only the lines that need fixing.
- If an issue cannot be auto-fixed safely, skip it.
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
                "diff": response.strip(),
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
    
    def _estimate_confidence(self, response: str) -> float:
        """Estimate confidence based on response characteristics."""
        # Simple heuristic: longer, more detailed responses = higher confidence
        word_count = len(response.split())
        
        if word_count > 100:
            return 0.9
        elif word_count > 50:
            return 0.7
        else:
            return 0.5