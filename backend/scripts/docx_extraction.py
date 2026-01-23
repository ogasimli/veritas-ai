#!/usr/bin/env python3
"""
Test script to extract markdown from .docx file.
Uses the actual ExtractorService from backend/app/services/extractor.py
"""

import sys
from pathlib import Path

# Add backend to path and import the actual ExtractorService
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Import directly from the extractor module to avoid triggering __init__.py issues
import importlib.util
extractor_path = backend_path / "app" / "services" / "extractor.py"
spec = importlib.util.spec_from_file_location("extractor", extractor_path)
extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor_module)

ExtractorService = extractor_module.ExtractorService


def main():
    # Path to the .docx file
    docx_path = Path(__file__).parent / ".docs" / "FILE_NAME.docx"
    
    if not docx_path.exists():
        print(f"Error: File not found at {docx_path}")
        return 1
    
    print(f"Reading file: {docx_path}")
    
    # Read the .docx file as bytes
    with open(docx_path, "rb") as f:
        doc_bytes = f.read()
    
    print(f"File size: {len(doc_bytes):,} bytes")
    
    # Create extractor service (the ACTUAL one from backend) and convert to markdown
    extractor = ExtractorService()
    print("\nExtracting markdown using ExtractorService from backend/app/services/extractor.py...")
    
    markdown_content = extractor.extract_markdown(doc_bytes)
    
    # Print some stats
    lines = markdown_content.split('\n')
    print(f"\nExtraction complete!")
    print(f"Lines extracted: {len(lines):,}")
    print(f"Characters: {len(markdown_content):,}")
    print(f"Tables found: {markdown_content.count('| --- |')}")
    
    # Save to a file
    output_path = Path(__file__).parent / ".docs" / "FILE_NAME_extracted.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"\nMarkdown saved to: {output_path}")
    
    # Print first 3000 characters as preview
    print("\n" + "="*80)
    print("PREVIEW (first 3000 characters):")
    print("="*80)
    print(markdown_content[:3000])
    if len(markdown_content) > 3000:
        print("\n... (truncated)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
