#!/usr/bin/env python3
import os
import sys
import argparse
import time
from collections import Counter
from analyzer.detectors.security import SecurityScanner
from analyzer.detectors.quality import QualityDetector
from analyzer.detectors.ai_patterns import AIPatternDetector
from colorama import Fore, Style, init

init(autoreset=True)

def benchmark_repo(repo_path: str):
    """Run static analysis on a directory and print high-signal vs low-signal density."""
    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Error: Path {repo_path} does not exist.{Style.RESET_ALL}")
        sys.exit(1)

    print(f"{Fore.CYAN}Starting FPR Benchmark on: {repo_path}{Style.RESET_ALL}")
    
    security_scanner = SecurityScanner()
    quality_detector = QualityDetector()
    ai_detector = AIPatternDetector()

    total_files = 0
    total_issues = 0
    issue_types = Counter()
    severity_counts = Counter()

    start_time = time.time()

    for root, _, files in os.walk(repo_path):
        if any(ignored in root for ignored in ['node_modules', '.git', 'venv', '__pycache__']):
            continue

        for file in files:
            if not file.endswith(('.py', '.js', '.ts', '.tsx', '.jsx')):
                continue

            filepath = os.path.join(root, file)
            lang = "python" if file.endswith('.py') else "javascript"

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    code = f.read()
            except Exception:
                continue

            total_files += 1
            
            # Run fast static engines
            sec_issues = security_scanner.scan(code, file, lang)
            qual_issues = quality_detector.detect(code, file, lang)
            ai_issues = ai_detector.detect(code, file, lang)

            all_issues = sec_issues + qual_issues + ai_issues
            total_issues += len(all_issues)

            for issue in all_issues:
                issue_types[issue['type']] += 1
                severity_counts[issue['severity']] += 1

    duration = time.time() - start_time

    # Output metrics
    print("\n" + "="*40)
    print(f"{Fore.GREEN}Benchmark Complete!{Style.RESET_ALL}")
    print(f"Files scanned: {total_files}")
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Total Issues Detected: {total_issues}")
    
    if total_files > 0:
        issues_per_file = total_issues / total_files
        print(f"Issue Density: {issues_per_file:.2f} issues/file")
        
        if issues_per_file > 3.0:
            print(f"{Fore.YELLOW}Warning: High density. Likely high False Positive Rate (>30%). Suggest tuning rules.{Style.RESET_ALL}")
        elif issues_per_file < 0.2:
            print(f"{Fore.YELLOW}Warning: Low density. Rules may be too lax.{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}Density nominal. Good Signal-to-Noise ratio.{Style.RESET_ALL}")

    print("\n--- Severity Ratio ---")
    for sev, count in severity_counts.most_common():
        print(f"- {sev.upper()}: {count}")

    print("\n--- Top 5 Triggered Rules (Check for noise) ---")
    for rule, count in issue_types.most_common(5):
        print(f"- {rule}: {count}")
    print("="*40)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IntelliReview FPR Benchmark Tool")
    parser.add_argument("path", help="Path to the repository directory to benchmark")
    args = parser.parse_args()
    
    benchmark_repo(args.path)
