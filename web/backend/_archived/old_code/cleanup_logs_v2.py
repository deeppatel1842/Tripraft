"""
Improved logging cleanup script - handles indentation correctly
Adds 'pass' statements where needed to maintain valid Python syntax
"""
import os
import re
import ast
from pathlib import Path
from datetime import datetime

# Directories to process
TARGET_DIRS = [
    Path(__file__).parent.parent / "api",
    Path(__file__).parent.parent / "expense_engine",
    Path(__file__).parent.parent / "Group_planner",
    Path(__file__).parent.parent / "services",
]

# Patterns to keep (security critical)
KEEP_PATTERNS = [
    r'logger\.error\(',
    r'logger\.warning\(',
    r'logger\.critical\(',
    r'logger\.exception\(',
]

# Patterns to remove (verbose/security risk)
REMOVE_PATTERNS = [
    r'logger\.info\(',
    r'logger\.debug\(',
]

def should_keep_log(line):
    """Check if log line should be kept"""
    for pattern in KEEP_PATTERNS:
        if re.search(pattern, line):
            return True
    return False

def should_remove_log(line):
    """Check if log line should be removed"""
    for pattern in REMOVE_PATTERNS:
        if re.search(pattern, line):
            return True
    return False

def get_indentation(line):
    """Get the indentation level of a line"""
    return len(line) - len(line.lstrip())

def process_file(filepath, execute=False):
    """Process a single Python file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return None, f"Error reading: {e}"
    
    modified_lines = []
    changes = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a logger line to remove
        if should_remove_log(line) and not should_keep_log(line):
            # Get the indentation of the logger line
            indent = get_indentation(line)
            
            # Comment out this line
            commented_line = ' ' * indent + '# ' + line.lstrip()
            modified_lines.append(commented_line)
            changes.append(f"Line {i+1}: Commented {line.strip()[:60]}")
            
            # Check if this is a multi-line statement
            original_line = line
            j = i + 1
            while j < len(lines) and (original_line.rstrip().endswith('\\') or 
                                     original_line.rstrip().endswith(',') and 
                                     original_line.count('(') > original_line.count(')')):
                continuation = lines[j]
                commented_continuation = ' ' * get_indentation(continuation) + '# ' + continuation.lstrip()
                modified_lines.append(commented_continuation)
                changes.append(f"Line {j+1}: Commented continuation")
                original_line = continuation
                j += 1
                i = j - 1
            
            # Check if the NEXT non-comment, non-blank line has LESS or EQUAL indentation
            # This means the commented logger was the only statement in its block
            next_idx = i + 1
            while next_idx < len(lines):
                next_line = lines[next_idx]
                stripped = next_line.strip()
                
                # Skip blank lines and comments
                if not stripped or stripped.startswith('#'):
                    next_idx += 1
                    continue
                    
                next_indent = get_indentation(next_line)
                
                # If next line has less or equal indentation, we need a pass statement
                if next_indent <= indent:
                    pass_line = ' ' * indent + 'pass  # Placeholder for commented log\n'
                    modified_lines.append(pass_line)
                    changes.append(f"Line {i+1}: Added 'pass' statement")
                    break
                else:
                    # Next line is more indented, so we're safe
                    break
            else:
                # We reached end of file, add pass if needed
                if i == len(lines) - 1:
                    pass_line = ' ' * indent + 'pass  # Placeholder for commented log\n'
                    modified_lines.append(pass_line)
                    changes.append(f"Line {i+1}: Added 'pass' statement (EOF)")
            
            i += 1
            continue
        
        # Keep the line as-is
        modified_lines.append(line)
        i += 1
    
    if not changes:
        return None, "No changes needed"
    
    # Validate syntax before saving
    try:
        ast.parse(''.join(modified_lines))
    except SyntaxError as e:
        return None, f"Syntax validation failed: {e}"
    
    if execute:
        # Create backup
        backup_path = filepath.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(''.join(lines))
        
        # Write modified content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
        
        return changes, f"✓ Modified (backup: {backup_path.name})"
    else:
        return changes, "✓ Would modify (dry run)"

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Clean up production logs v2')
    parser.add_argument('--execute', action='store_true', help='Actually modify files')
    args = parser.parse_args()
    
    print("=" * 80)
    print("LOGGING CLEANUP v2 - IMPROVED INDENTATION HANDLING")
    print("=" * 80)
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
    print()
    
    all_files = []
    for target_dir in TARGET_DIRS:
        if target_dir.exists():
            all_files.extend(target_dir.rglob("*.py"))
    
    total_changed = 0
    total_changes = 0
    report_lines = []
    
    for filepath in all_files:
        changes, status = process_file(filepath, args.execute)
        
        if changes:
            total_changed += 1
            total_changes += len(changes)
            rel_path = filepath.relative_to(Path(__file__).parent.parent)
            print(f"\n{rel_path}")
            print(f"  {status}")
            print(f"  Changes: {len(changes)}")
            
            report_lines.append(f"\n{rel_path} ({len(changes)} changes):")
            for change in changes[:5]:  # Show first 5
                print(f"    • {change}")
                report_lines.append(f"  • {change}")
            if len(changes) > 5:
                print(f"    ... and {len(changes) - 5} more")
                report_lines.append(f"  ... and {len(changes) - 5} more")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files changed: {total_changed}")
    print(f"Total changes: {total_changes}")
    print()
    print("✓ All files validated for syntax correctness")
    print()
    
    if args.execute:
        report_path = Path(__file__).parent.parent / "_archived" / f"logging_cleanup_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("LOGGING CLEANUP v2 REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Files changed: {total_changed}\n")
            f.write(f"Total changes: {total_changes}\n\n")
            f.write("CHANGES:\n")
            f.writelines(report_lines)
        print(f"Report saved: {report_path}")

if __name__ == "__main__":
    main()
