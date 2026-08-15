#!/usr/bin/env python3
"""
Detect silent exception handlers in Python code.

Finds patterns like:
  except Exception: pass
  except: pass
  except SomeError: continue
  except: return

This is a code smell that indicates potential bugs or missing error handling.

Usage:
  python scripts/check_silent_exceptions.py [--fix]
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns that indicate silent exception handling
SILENT_EXCEPTION_PATTERNS = [
    # except ... : pass (with various whitespace)
    r'except\s+\w+\s*:\s*pass\s*(?:#|$|\n)',
    r'except\s+\w+\s*,\s*\w+\s*:\s*pass\s*(?:#|$|\n)',
    # except ... : continue
    r'except\s+\w+\s*:\s*continue\s*(?:#|$|\n)',
    # except ... : (no handler, just pass)
    r'except\s*:\s*pass\s*(?:#|$|\n)',
    # except ... : return (silently ignores error)
    r'except\s+\w+\s*:\s*return\s*(?:#|$|\n)',
]

def find_silent_exceptions(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Find silent exception handlers in a Python file.

    Returns:
        List of (line_number, line_content, pattern_matched)
    """
    findings = []

    try:
        content = file_path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, IsADirectoryError):
        return findings

    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        for pattern in SILENT_EXCEPTION_PATTERNS:
            if re.search(pattern, line):
                findings.append((line_num, line.strip(), pattern))
                break

    return findings

def main():
    """Scan backend/ for silent exception handlers."""
    backend_dir = Path(__file__).parent.parent / 'backend'

    if not backend_dir.exists():
        print(f"❌ Backend directory not found: {backend_dir}")
        sys.exit(1)

    total_findings = 0
    files_with_issues = []

    # Scan all .py files
    for py_file in sorted(backend_dir.rglob('*.py')):
        findings = find_silent_exceptions(py_file)

        if findings:
            files_with_issues.append((py_file, findings))
            total_findings += len(findings)

            print(f"\n🔴 {py_file.relative_to(backend_dir.parent)}")
            for line_num, line_content, pattern in findings:
                print(f"   Line {line_num}: {line_content}")

    # Summary
    print(f"\n{'='*60}")
    if total_findings == 0:
        print("[OK] No silent exceptions found!")
        sys.exit(0)
    else:
        print(f"[ERROR] Found {total_findings} silent exception handler(s)")
        print(f"   in {len(files_with_issues)} file(s)")
        print(f"\nRecommendation:")
        print("  - Add logging: logger.exception('Unexpected error')")
        print("  - Or re-raise: raise")
        print("  - Or handle specifically: except ValueError as e: ...")
        sys.exit(1)

if __name__ == '__main__':
    main()
