#!/usr/bin/env python3
"""Fix TS6133 (unused imports/variables) errors in frontend."""
import subprocess, re, os

os.chdir("/workspaces/stellar-privacy-analytics/frontend")

# Get all TS6133 errors
result = subprocess.run(["npx", "tsc", "--noEmit"], capture_output=True, text=True, timeout=120)
errors = [l for l in result.stderr.split("\n") + result.stdout.split("\n") if "TS6133" in l and "error" in l]

# Parse: src/file.tsx(line,col): error TS6133: 'Name' is declared but its value is never read.
parsed = []
for e in errors:
    m = re.match(r"([^(]+)\((\d+),\d+\): error TS6133: '([^']+)' is declared but its value is never read", e.strip())
    if m:
        parsed.append((m.group(1).strip(), int(m.group(2)), m.group(3)))

# Group by file
from collections import defaultdict
by_file = defaultdict(list)
for fpath, line, name in parsed:
    by_file[fpath].append((line, name))

fixed_count = 0
for fpath, items in by_file.items():
    if not os.path.exists(fpath):
        continue
    with open(fpath) as fh:
        lines = fh.readlines()
    
    # Build set of unused names and their line numbers
    unused = {name for _, name in items}
    
    new_lines = []
    for i, line_content in enumerate(lines):
        curr_line = i + 1  # 1-based
        
        # Check if this line has an unused import
        modified = False
        for line_num, name in items:
            if curr_line == line_num:
                # Check if this is an import line
                if 'import' in line_content and name in line_content:
                    # Remove the unused import from the import statement
                    # Pattern: import { A, B, C } from "module"
                    # Pattern: import A from "module"  
                    # Pattern: import { A } from "module"
                    if re.match(r"\s*import\s+\{[^}]+\}\s+from", line_content):
                        # Remove the name from the import list
                        new_import = re.sub(
                            r'\b' + re.escape(name) + r'\s*,?\s*',
                            '', line_content
                        )
                        # Clean up empty braces or extra commas
                        new_import = re.sub(r'\{\s*,', '{', new_import)
                        new_import = re.sub(r',\s*\}', '}', new_import)
                        new_import = re.sub(r'\{\s*\}', '', new_import)
                        # If the whole import became empty (no more imports), remove the line
                        if 'from' in new_import and re.search(r'import\s+\{\s*\}\s+from', new_import):
                            line_content = ''  # Remove the empty import line
                        elif new_import.strip():
                            line_content = new_import
                        modified = True
                        fixed_count += 1
                    elif re.match(r"\s*import\s+\w+\s+from", line_content):
                        # Default import - remove the whole line
                        line_content = ''
                        modified = True
                        fixed_count += 1
                else:
                    # Variable declaration - prefix with _
                    if not name.startswith('_') and not modified:
                        line_content = re.sub(
                            r'\b(let|const|var)\s+(' + re.escape(name) + r')\b',
                            r'\1 _\2',
                            line_content
                        )
                        if '_' + name in line_content:
                            modified = True
                            fixed_count += 1
        
        new_lines.append(line_content)
    
    with open(fpath, 'w') as fh:
        fh.writelines(new_lines)

print(f"Fixed {fixed_count} TS6133 errors in {len(by_file)} files")
