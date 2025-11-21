"""
Professional Code Cleanup Script for Phase 1
============================================
Systematically updates Python files to use production-ready logging.

Features:
- Replace print() with proper logger
- Add production config imports
- No file deletion (archive unused files)
- Detailed reporting
- Manual review checkpoints

Author: Production Team
Date: November 18, 2025
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime


class PythonFileCleanup:
    """Professional Python file cleanup utility"""
    
    def __init__(self, root_path: str):
        """
        Initialize cleanup utility
        
        Args:
            root_path: Root directory to process
        """
        self.root_path = Path(root_path)
        self.changes_made = []
        self.files_processed = 0
        self.print_statements_found = 0
        
    def analyze_file(self, file_path: Path) -> Dict:
        """
        Analyze a Python file for cleanup opportunities
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Dict with analysis results
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            issues = {
                'file': str(file_path.relative_to(self.root_path)),
                'print_statements': [],
                'missing_logger': False,
                'hardcoded_values': [],
                'needs_config_import': False
            }
            
            # Find print statements (excluding comments)
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                    
                if 'print(' in line and not 'Blueprint' in line:
                    issues['print_statements'].append({
                        'line': i,
                        'content': line.strip()
                    })
            
            # Check if file already has logger
            if 'get_logger' not in content and 'logging.getLogger' not in content:
                if len(issues['print_statements']) > 0:
                    issues['missing_logger'] = True
            
            # Check for hardcoded values (simple detection)
            hardcoded_patterns = [
                (r'clock_skew\s*=\s*\d+', 'AuthConfig.CLOCK_SKEW_TOLERANCE'),
                (r'ttl\s*=\s*\d+', 'CacheConfig.TTL_*'),
                (r'max_size\s*=\s*\d+', 'PaginationConfig.MAX_PAGE_SIZE'),
            ]
            
            for pattern, suggestion in hardcoded_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    issues['hardcoded_values'].append({
                        'line': line_num,
                        'match': match.group(),
                        'suggestion': suggestion
                    })
            
            return issues
        
        except Exception as e:
            return {
                'file': str(file_path),
                'error': str(e)
            }
    
    def update_file_imports(self, file_path: Path) -> bool:
        """
        Add production logging imports to file
        
        Args:
            file_path: Path to Python file
            
        Returns:
            bool: Success status
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if imports already exist
            if 'from expense_engine.logging_utils import get_logger' in content:
                return False  # Already has imports
            
            # Find the right place to add imports
            lines = content.split('\n')
            import_index = 0
            
            # Find last import statement
            for i, line in enumerate(lines):
                if line.startswith('from ') or line.startswith('import '):
                    import_index = i + 1
            
            # Add our imports
            new_imports = [
                'from expense_engine.logging_utils import get_logger',
                ''
            ]
            
            lines.insert(import_index, '\n'.join(new_imports))
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            return True
        
        except Exception as e:
            print(f"Error updating imports in {file_path}: {e}")
            return False
    
    def replace_print_statements(self, file_path: Path, dry_run: bool = True) -> int:
        """
        Replace print() statements with proper logging
        
        Args:
            file_path: Path to Python file
            dry_run: If True, only show what would change
            
        Returns:
            int: Number of replacements made
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            replacements = 0
            new_lines = []
            
            # Add logger initialization at top (after imports)
            logger_added = False
            
            for i, line in enumerate(lines):
                # Skip if this is a Blueprint line or comment
                if 'Blueprint' in line or line.strip().startswith('#'):
                    new_lines.append(line)
                    continue
                
                # Add logger after imports
                if not logger_added and (line.startswith('from ') or line.startswith('import ')):
                    # Check if next line is not an import
                    if i + 1 < len(lines) and not lines[i + 1].startswith(('from ', 'import ')):
                        new_lines.append(line)
                        if 'get_logger' in content:  # Only add if imports exist
                            new_lines.append('')
                            new_lines.append('logger = get_logger(__name__)')
                            logger_added = True
                        continue
                
                # Replace print statements
                if 'print(' in line and not logger_added and 'get_logger' not in content:
                    new_lines.append(line)  # Keep as-is if no logger
                    continue
                
                if 'print(' in line and logger_added:
                    # Extract the print content
                    indent = len(line) - len(line.lstrip())
                    
                    # Simple replacement
                    if 'print("✅' in line or 'print("✓' in line:
                        # Success message
                        new_line = ' ' * indent + line.replace('print(', 'logger.info(')
                    elif 'print("❌' in line or 'print("⚠️' in line:
                        # Error/warning message
                        new_line = ' ' * indent + line.replace('print(', 'logger.warning(')
                    else:
                        # Regular info
                        new_line = ' ' * indent + line.replace('print(', 'logger.info(')
                    
                    new_lines.append(new_line)
                    replacements += 1
                else:
                    new_lines.append(line)
            
            if not dry_run and replacements > 0:
                # Write changes
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
            
            return replacements
        
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return 0
    
    def generate_report(self, issues_list: List[Dict]) -> str:
        """
        Generate cleanup report
        
        Args:
            issues_list: List of file issues
            
        Returns:
            str: Formatted report
        """
        report = []
        report.append("\n" + "=" * 80)
        report.append("PHASE 1 CLEANUP ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Files Analyzed: {len(issues_list)}")
        report.append("")
        
        total_prints = 0
        files_need_logger = 0
        total_hardcoded = 0
        
        for issues in issues_list:
            if 'error' in issues:
                continue
            
            print_count = len(issues.get('print_statements', []))
            total_prints += print_count
            
            if issues.get('missing_logger'):
                files_need_logger += 1
            
            total_hardcoded += len(issues.get('hardcoded_values', []))
            
            if print_count > 0 or issues.get('missing_logger') or len(issues.get('hardcoded_values', [])) > 0:
                report.append(f"\n📄 {issues['file']}")
                report.append("-" * 60)
                
                if print_count > 0:
                    report.append(f"   🔍 {print_count} print() statement(s) found:")
                    for stmt in issues['print_statements'][:5]:  # Show first 5
                        report.append(f"      Line {stmt['line']}: {stmt['content'][:70]}")
                    if print_count > 5:
                        report.append(f"      ... and {print_count - 5} more")
                
                if issues.get('missing_logger'):
                    report.append(f"   ⚠️  Missing logger initialization")
                
                if issues.get('hardcoded_values'):
                    report.append(f"   🎯 {len(issues['hardcoded_values'])} hardcoded value(s):")
                    for hc in issues['hardcoded_values'][:3]:
                        report.append(f"      Line {hc['line']}: {hc['match']} → {hc['suggestion']}")
        
        report.append("\n" + "=" * 80)
        report.append("SUMMARY")
        report.append("=" * 80)
        report.append(f"Total print() statements:     {total_prints}")
        report.append(f"Files needing logger:         {files_need_logger}")
        report.append(f"Hardcoded values found:       {total_hardcoded}")
        report.append("")
        report.append("RECOMMENDED ACTIONS:")
        report.append("1. Review this report carefully")
        report.append("2. Run cleanup with --execute flag")
        report.append("3. Manually verify critical files")
        report.append("4. Run tests after changes")
        report.append("=" * 80)
        
        return '\n'.join(report)


def main():
    """Main execution"""
    import sys
    
    # Configuration
    backend_path = r"c:\Users\Kashyap\Documents\Deep\Travel\web\backend"
    
    # Target directories
    target_dirs = [
        'api',
        'services',
        'database',
    ]
    
    # Files to analyze
    files_to_check = []
    for dir_name in target_dirs:
        dir_path = Path(backend_path) / dir_name
        if dir_path.exists():
            files_to_check.extend(dir_path.glob('*.py'))
    
    print("\n🔍 Starting Phase 1 Code Analysis...")
    print(f"📂 Backend Path: {backend_path}")
    print(f"📊 Files to analyze: {len(files_to_check)}")
    
    # Analyze files
    cleanup = PythonFileCleanup(backend_path)
    issues_list = []
    
    for file_path in files_to_check:
        if '__pycache__' in str(file_path) or 'test' in str(file_path).lower():
            continue
        
        issues = cleanup.analyze_file(file_path)
        issues_list.append(issues)
    
    # Generate report
    report = cleanup.generate_report(issues_list)
    print(report)
    
    # Save report
    report_path = Path(backend_path) / '_archived' / f'cleanup_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n💾 Report saved to: {report_path}")
    print("\n✅ Analysis complete! Review report before proceeding.")


if __name__ == '__main__':
    main()
