"""
Automated Script to Clean Up Logging and Print Statements
Removes/sanitizes all console.log, print(), and excessive logging for production
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict


class LogCleanupReport:
    """Track cleanup statistics"""
    def __init__(self):
        self.files_scanned = 0
        self.files_modified = 0
        self.lines_removed = 0
        self.lines_sanitized = 0
        self.issues = []
    
    def add_issue(self, file_path: str, line_num: int, issue: str):
        self.issues.append((file_path, line_num, issue))
    
    def print_report(self):
        print("\n" + "="*80)
        print("CLEANUP REPORT")
        print("="*80)
        print(f"Files Scanned: {self.files_scanned}")
        print(f"Files Modified: {self.files_modified}")
        print(f"Lines Removed: {self.lines_removed}")
        print(f"Lines Sanitized: {self.lines_sanitized}")
        print(f"\nIssues Found: {len(self.issues)}")
        
        if self.issues:
            print("\nDETAILED ISSUES:")
            for file_path, line_num, issue in self.issues:
                print(f"  {file_path}:{line_num} - {issue}")


class LogCleaner:
    """Clean up logging statements for production"""
    
    # Patterns to detect logging
    PATTERNS = {
        'python_print': re.compile(r'^\s*print\s*\('),
        'python_logger_debug': re.compile(r'^\s*logger\.(debug|info)\s*\('),
        'python_logger_excessive': re.compile(r'logger\.info.*(?:Cache|Hit|Miss|Fetching|Retrieved)'),
        'js_console_log': re.compile(r'^\s*console\.(log|debug|info)\s*\('),
        'js_console_warn': re.compile(r'^\s*console\.warn\s*\('),
        'credential_leak': re.compile(r'(password|token|secret|api_key|credential)[\s\'"]*[=:)]', re.IGNORECASE),
        'user_id_raw': re.compile(r'(user_id|uid|g\.user_id)(?!\s*[:=]\s*ProductionLogger\.hash_id)'),
    }
    
    # Safe patterns to keep
    SAFE_PATTERNS = {
        'error_logs': re.compile(r'logger\.(error|critical|exception)'),
        'warning_logs': re.compile(r'logger\.warning'),
        'dev_guard': re.compile(r'if.*NODE_ENV.*development|if.*DEBUG|if.*IS_DEBUG'),
    }
    
    def __init__(self, backend_path: str, frontend_path: str, dry_run: bool = False):
        self.backend_path = Path(backend_path)
        self.frontend_path = Path(frontend_path)
        self.dry_run = dry_run
        self.report = LogCleanupReport()
    
    def clean_python_file(self, file_path: Path) -> Tuple[List[str], int, int]:
        """Clean a Python file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        removed = 0
        sanitized = 0
        in_multiline_print = False
        
        for i, line in enumerate(lines, 1):
            original_line = line
            keep_line = True
            
            # Check for multi-line print statements
            if in_multiline_print:
                if ')' in line:
                    in_multiline_print = False
                keep_line = False
                removed += 1
                continue
            
            # Remove standalone print statements
            if self.PATTERNS['python_print'].match(line):
                if '(' in line and ')' not in line:
                    in_multiline_print = True
                keep_line = False
                removed += 1
                self.report.add_issue(str(file_path), i, "Removed print() statement")
                continue
            
            # Remove excessive logger.debug/info for cache operations
            if self.PATTERNS['python_logger_excessive'].search(line):
                # Check if it's in a conditional block
                indent = len(line) - len(line.lstrip())
                if indent == 0 or 'if' not in ''.join(lines[max(0, i-3):i]):
                    keep_line = False
                    removed += 1
                    self.report.add_issue(str(file_path), i, "Removed excessive cache logging")
                    continue
            
            # Sanitize credential leaks
            if self.PATTERNS['credential_leak'].search(line) and 'logger' in line.lower():
                # Replace with [REDACTED]
                line = re.sub(
                    r'(password|token|secret|api_key|credential)[\s\'"]*(=|:)\s*[\'"]?[^\'"]+[\'"]?',
                    r'\1\2"[REDACTED]"',
                    line,
                    flags=re.IGNORECASE
                )
                sanitized += 1
                self.report.add_issue(str(file_path), i, "Sanitized credential in log")
            
            # Keep safe patterns (errors, warnings)
            if any(pattern.search(line) for pattern in self.SAFE_PATTERNS.values()):
                new_lines.append(line)
                continue
            
            if keep_line:
                new_lines.append(line)
        
        return new_lines, removed, sanitized
    
    def clean_javascript_file(self, file_path: Path) -> Tuple[List[str], int, int]:
        """Clean a JavaScript/JSX file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        removed = 0
        sanitized = 0
        in_dev_guard = False
        dev_guard_indent = 0
        
        for i, line in enumerate(lines, 1):
            # Check for development guard
            if self.SAFE_PATTERNS['dev_guard'].search(line):
                in_dev_guard = True
                dev_guard_indent = len(line) - len(line.lstrip())
                new_lines.append(line)
                continue
            
            # Exit dev guard when indentation decreases
            if in_dev_guard:
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= dev_guard_indent and line.strip() and not line.strip().startswith('//'):
                    in_dev_guard = False
                new_lines.append(line)
                continue
            
            # Remove console.log/debug/info (but keep error/warn)
            if self.PATTERNS['js_console_log'].match(line):
                # Wrap in development guard instead of removing
                indent = ' ' * (len(line) - len(line.lstrip()))
                new_lines.append(f"{indent}if (process.env.NODE_ENV === 'development') {{\n")
                new_lines.append(f"  {line}")
                new_lines.append(f"{indent}}}\n")
                sanitized += 1
                self.report.add_issue(str(file_path), i, "Wrapped console.log in dev guard")
                continue
            
            new_lines.append(line)
        
        return new_lines, removed, sanitized
    
    def process_file(self, file_path: Path):
        """Process a single file"""
        self.report.files_scanned += 1
        
        if file_path.suffix == '.py':
            new_lines, removed, sanitized = self.clean_python_file(file_path)
        elif file_path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
            new_lines, removed, sanitized = self.clean_javascript_file(file_path)
        else:
            return
        
        if removed > 0 or sanitized > 0:
            self.report.files_modified += 1
            self.report.lines_removed += removed
            self.report.lines_sanitized += sanitized
            
            if not self.dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                print(f"✅ Cleaned: {file_path} (removed: {removed}, sanitized: {sanitized})")
            else:
                print(f"🔍 Would clean: {file_path} (remove: {removed}, sanitize: {sanitized})")
    
    def run(self):
        """Run the cleanup process"""
        print("="*80)
        print("STARTING LOG CLEANUP")
        print("="*80)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Backend Path: {self.backend_path}")
        print(f"Frontend Path: {self.frontend_path}")
        print("="*80)
        
        # Process backend Python files
        print("\n📁 Processing Backend Files...")
        for py_file in self.backend_path.rglob('*.py'):
            if '__pycache__' not in str(py_file) and 'venv' not in str(py_file):
                self.process_file(py_file)
        
        # Process frontend JS/JSX files
        print("\n📁 Processing Frontend Files...")
        for js_file in self.frontend_path.rglob('*.{js,jsx}'):
            if 'node_modules' not in str(js_file):
                self.process_file(js_file)
        
        # Print report
        self.report.print_report()
        
        if self.dry_run:
            print("\n⚠️  This was a DRY RUN. No files were modified.")
            print("   Run with --execute flag to apply changes.")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up logging for production')
    parser.add_argument('--backend', default=r'c:\Users\Kashyap\Documents\Deep\Travel\web\backend\expense_engine',
                       help='Path to backend directory')
    parser.add_argument('--frontend', default=r'c:\Users\Kashyap\Documents\Deep\Travel\web\frontend\src\components\expenses',
                       help='Path to frontend directory')
    parser.add_argument('--execute', action='store_true',
                       help='Actually modify files (default is dry-run)')
    
    args = parser.parse_args()
    
    cleaner = LogCleaner(
        backend_path=args.backend,
        frontend_path=args.frontend,
        dry_run=not args.execute
    )
    
    cleaner.run()
    
    print("\n✅ Cleanup complete!")


if __name__ == '__main__':
    main()
