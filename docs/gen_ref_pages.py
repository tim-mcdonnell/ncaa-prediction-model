"""Generate the code reference pages."""

import os
from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

# Source directory
src_dir = Path("src")
# Output directory in docs
reference_dir = Path("reference")

# Iterate over Python files in the source directory
for path in sorted(src_dir.rglob("*.py")):
    module_path = path.relative_to(src_dir).with_suffix("")
    doc_path = path.relative_to(src_dir).with_suffix(".md")
    full_doc_path = reference_dir / doc_path

    # Skip __init__.py files with no content
    if module_path.name == "__init__" and path.stat().st_size <= 100:
        continue

    # Module path as dot notation
    module_dots = ".".join(module_path.parts)
    
    # Handle __init__.py specially
    if module_path.name == "__init__":
        module_dots = ".".join(module_path.parts[:-1])
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    
    # Skip if the module is empty or just has docstring
    if path.stat().st_size <= 2:
        continue

    # Create the markdown file
    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        fd.write(f"# `{module_dots}`\n\n")
        fd.write(f":::{module_dots}\n")

    # Add to navigation
    nav_parts = list(module_path.parts)
    
    if nav_parts[-1] == "__init__":
        nav_parts = nav_parts[:-1]
        
    nav[nav_parts] = doc_path.as_posix()

# Generate the navigation file
with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav()) 