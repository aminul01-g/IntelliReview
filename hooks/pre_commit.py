#!/usr/bin/env python3
import sys
import subprocess
import os

def run_analysis():
    """Run IntelliReview analysis on staged files."""
    # Get list of staged files
    try:
        output = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True)
        staged_files = output.strip().split('\n')
    except subprocess.CalledProcessError:
        print("Error: Could not list staged files.")
        return 0

    # Filter supported files
    supported_extensions = ['.py', '.js', '.java']
    files_to_analyze = [f for f in staged_files if any(f.endswith(ext) for ext in supported_extensions)]

    if not files_to_analyze:
        return 0

    print(f"IntelliReview: Analyzing {len(files_to_analyze)} staged files...")
    
    # Run CLI analysis
    # Assuming the CLI is available as 'intellireview' or via the path
    cli_path = os.path.join(os.getcwd(), 'cli', 'cli.py')
    
    total_severe_issues = 0
    
    for file_path in files_to_analyze:
        if not os.path.exists(file_path):
            continue
            
        try:
            # Run the CLI and capture JSON output
            cmd = [sys.executable, cli_path, 'analyze', file_path, '--output', 'json']
            result_json = subprocess.check_output(cmd, text=True)
            result = json.loads(result_json)
            
            issues = result.get('issues', [])
            severe_issues = [i for i in issues if i.get('severity') in ['critical', 'high']]
            
            if severe_issues:
                print(f"\n[!] {file_path}: Found {len(severe_issues)} critical/high issues.")
                for issue in severe_issues:
                    print(f"    Line {issue['line']}: {issue['message']}")
                total_severe_issues += len(severe_issues)
                
        except Exception as e:
            # If CLI fails, we might just warn or let it pass
            print(f"Warning: Failed to analyze {file_path}: {e}")

    if total_severe_issues > 0:
        print(f"\n[ERROR] Commit blocked. Found {total_severe_issues} severe code issues.")
        print("Please fix the issues above or use 'git commit --no-verify' to bypass.")
        return 1
        
    print("IntelliReview: No severe issues found. Commit allowed.")
    return 0

if __name__ == "__main__":
    import json
    sys.exit(run_analysis())
