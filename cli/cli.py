import click
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel
from rich.syntax import Syntax
import requests
import json
from typing import Optional

console = Console()

# API Configuration
API_BASE_URL = os.getenv('INTELLIREVIEW_API_URL', 'http://localhost:8000/api/v1')
CONFIG_FILE = Path.home() / '.intellireview' / 'config.json'

# Configuration Management

class Config:
    """Manage CLI configuration."""
    
    def __init__(self):
        self.config_dir = Path.home() / '.intellireview'
        self.config_file = self.config_dir / 'config.json'
        self.config = self.load()
    
    def load(self) -> dict:
        """Load configuration."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save(self):
        """Save configuration."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value."""
        self.config[key] = value
        self.save()


config = Config()

# API Client

class APIClient:
    """API client for IntelliReview."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.token = config.get('token')
    
    def _headers(self) -> dict:
        """Get request headers."""
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
    
    def login(self, username: str, password: str) -> dict:
        """Login and get token."""
        response = requests.post(
            f'{self.base_url}/auth/login',
            data={'username': username, 'password': password}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            config.set('token', self.token)
            return data
        else:
            raise Exception(f"Login failed: {response.json().get('detail')}")
    
    def analyze(self, code: str, language: str, file_path: str = None) -> dict:
        """Analyze code."""
        payload = {
            'code': code,
            'language': language,
            'file_path': file_path
        }
        
        response = requests.post(
            f'{self.base_url}/analysis/analyze',
            json=payload,
            headers=self._headers()
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Analysis failed: {response.json().get('detail')}")
    
    def get_metrics(self) -> dict:
        """Get user metrics."""
        response = requests.get(
            f'{self.base_url}/metrics/user',
            headers=self._headers()
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get metrics: {response.json().get('detail')}")


api = APIClient()

# CLI Commands


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """IntelliReview - AI-Powered Code Review Assistant"""
    pass


@cli.command()
@click.option('--username', prompt=True, help='Username')
@click.option('--password', prompt=True, hide_input=True, help='Password')
def login(username: str, password: str):
    """Login to IntelliReview."""
    try:
        with console.status("[bold green]Logging in..."):
            result = api.login(username, password)
        
        console.print(f"[green]✓[/green] Successfully logged in as {username}")
        console.print(f"Token expires in: {result.get('expires_in', 'N/A')}")
    
    except Exception as e:
        console.print(f"[red]✗[/red] Login failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--language', '-l', help='Programming language (auto-detected if not specified)')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text', help='Output format')
def analyze(file_path: str, language: Optional[str], output: str):
    """Analyze a source code file."""
    
    # Read file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to read file: {str(e)}")
        sys.exit(1)
    
    # Detect language if not specified
    if not language:
        ext = Path(file_path).suffix
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.java': 'java'
        }
        language = lang_map.get(ext)
        
        if not language:
            console.print(f"[red]✗[/red] Could not detect language. Please specify with -l")
            sys.exit(1)
    
    # Analyze
    try:
        with console.status(f"[bold green]Analyzing {file_path}..."):
            result = api.analyze(code, language, file_path)
        
        if output == 'json':
            console.print_json(data=result)
        else:
            display_analysis_results(result, file_path)
    
    except Exception as e:
        console.print(f"[red]✗[/red] Analysis failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True, help='Analyze recursively')
@click.option('--language', '-l', help='Filter by language')
def analyze_dir(directory: str, recursive: bool, language: Optional[str]):
    """Analyze all files in a directory."""
    
    dir_path = Path(directory)
    
    # Find files
    patterns = ['*.py', '*.js', '*.java']
    if language:
        ext_map = {'python': '*.py', 'javascript': '*.js', 'java': '*.java'}
        patterns = [ext_map.get(language, '*.py')]
    
    files = []
    for pattern in patterns:
        if recursive:
            files.extend(dir_path.rglob(pattern))
        else:
            files.extend(dir_path.glob(pattern))
    
    if not files:
        console.print(f"[yellow]No files found in {directory}")
        return
    
    console.print(f"[cyan]Found {len(files)} files to analyze[/cyan]\n")
    
    total_issues = 0
    
    with Progress() as progress:
        task = progress.add_task("[green]Analyzing...", total=len(files))
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Detect language
                ext = file_path.suffix
                lang_map = {'.py': 'python', '.js': 'javascript', '.java': 'java'}
                lang = lang_map.get(ext, 'python')
                
                result = api.analyze(code, lang, str(file_path))
                issues_count = len(result.get('issues', []))
                total_issues += issues_count
                
                if issues_count > 0:
                    console.print(f"  {file_path}: [red]{issues_count} issues[/red]")
            
            except Exception as e:
                console.print(f"  [red]✗[/red] {file_path}: {str(e)}")
            
            progress.update(task, advance=1)
    
    console.print(f"\n[cyan]Total issues found: {total_issues}[/cyan]")


@cli.command()
def stats():
    """Show your code analysis statistics."""
    
    try:
        with console.status("[bold green]Fetching statistics..."):
            metrics = api.get_metrics()
        
        # Create table
        table = Table(title="Your IntelliReview Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Analyses", str(metrics.get('total_analyses', 0)))
        table.add_row("This Week", str(metrics.get('weekly_analyses', 0)))
        table.add_row("Member Since", metrics.get('user_since', 'N/A'))
        
        console.print(table)
        
        # Language breakdown
        if 'language_breakdown' in metrics:
            console.print("\n[cyan]Language Breakdown:[/cyan]")
            lang_table = Table()
            lang_table.add_column("Language", style="cyan")
            lang_table.add_column("Count", style="green")
            
            for lang, count in metrics['language_breakdown'].items():
                lang_table.add_row(lang, str(count))
            
            console.print(lang_table)
    
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to fetch statistics: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--key', '-k', required=True, help='Configuration key')
@click.option('--value', '-v', required=True, help='Configuration value')
def config_set(key: str, value: str):
    """Set configuration value."""
    config.set(key, value)
    console.print(f"[green]✓[/green] Set {key} = {value}")


@cli.command()
@click.option('--key', '-k', help='Configuration key (show all if not specified)')
def config_get(key: Optional[str]):
    """Get configuration value."""
    if key:
        value = config.get(key)
        if value:
            console.print(f"{key} = {value}")
        else:
            console.print(f"[yellow]Key '{key}' not found[/yellow]")
    else:
        # Show all config
        table = Table(title="IntelliReview Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        
        for k, v in config.config.items():
            # Hide sensitive values
            if 'token' in k.lower() or 'password' in k.lower():
                v = '*' * 8
            table.add_row(k, str(v))
        
        console.print(table)


@cli.command()
def init():
    """Initialize IntelliReview in current directory."""
    
    current_dir = Path.cwd()
    config_file = current_dir / '.intellireview.yml'
    
    if config_file.exists():
        console.print("[yellow]IntelliReview is already initialized in this directory[/yellow]")
        return
    
    # Create default config
    default_config = """# IntelliReview Configuration
version: 1.0

# Analysis settings
analysis:
  languages:
    - python
    - javascript
    - java
  
  ignore:
    - node_modules/
    - venv/
    - __pycache__/
    - "*.min.js"
  
  rules:
    complexity_threshold: 10
    line_length: 100
    max_function_length: 50

# Reporting
reporting:
  format: text
  output_file: intellireview_report.txt
"""
    
    with open(config_file, 'w') as f:
        f.write(default_config)
    
    console.print(f"[green]✓[/green] Initialized IntelliReview in {current_dir}")
    console.print(f"Configuration file created: {config_file}")


# Display Helpers

def display_analysis_results(result: dict, file_path: str):
    """Display analysis results in a formatted way."""
    
    # Header
    console.print(Panel(
        f"[bold cyan]Analysis Results: {file_path}[/bold cyan]",
        border_style="cyan"
    ))
    
    # Metrics
    metrics = result.get('metrics', {})
    
    metrics_table = Table(title="Code Metrics")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", style="green")
    
    metrics_table.add_row("Lines of Code", str(metrics.get('lines_of_code', 'N/A')))
    metrics_table.add_row("Complexity", str(metrics.get('complexity', 'N/A')))
    metrics_table.add_row("Maintainability Index", str(metrics.get('maintainability_index', 'N/A')))
    
    console.print(metrics_table)
    console.print()
    
    # Issues
    issues = result.get('issues', [])
    
    if not issues:
        console.print("[green]✓ No issues found![/green]")
        return
    
    # Group by severity
    severity_order = ['critical', 'high', 'medium', 'low', 'info']
    issues_by_severity = {sev: [] for sev in severity_order}
    
    for issue in issues:
        severity = issue.get('severity', 'info')
        issues_by_severity[severity].append(issue)
    
    # Display issues
    for severity in severity_order:
        severity_issues = issues_by_severity[severity]
        if not severity_issues:
            continue
        
        color_map = {
            'critical': 'red',
            'high': 'red',
            'medium': 'yellow',
            'low': 'blue',
            'info': 'cyan'
        }
        
        color = color_map.get(severity, 'white')
        
        console.print(f"\n[bold {color}]{severity.upper()} ({len(severity_issues)} issues)[/bold {color}]")
        
        for i, issue in enumerate(severity_issues, 1):
            line = issue.get('line', 'N/A')
            issue_type = issue.get('type', 'unknown')
            message = issue.get('message', 'No message')
            suggestion = issue.get('suggestion', '')
            
            console.print(f"  [{i}] Line {line} - {issue_type}")
            console.print(f"      {message}")
            
            if suggestion:
                console.print(f"      [dim]💡 {suggestion}[/dim]")
            
            console.print()

# Entry Point

if __name__ == "__main__":
    cli()