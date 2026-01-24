#!/usr/bin/env python3
"""
Extract markdown from .docx files using the ExtractorService.
Uses the actual ExtractorService from backend/app/services/extractor.py
"""

import argparse
import os
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
    parser = argparse.ArgumentParser(
        description="Extract markdown from a .docx file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/docx_extraction.py "/absolute/path/to/document.docx"
  uv run python scripts/docx_extraction.py "~/Desktop/document.docx"

Note: If the path contains spaces, wrap it in quotes.
        """,
    )
    parser.add_argument("file", type=str, help="Path to the .docx file (can use ~ for home directory)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path for the markdown file (default: same directory as input with .md extension)",
    )

    args = parser.parse_args()

    # Handle tilde expansion and resolve path
    expanded_path = os.path.expanduser(args.file)
    docx_path = Path(expanded_path).resolve()

    if not docx_path.exists():
        print(f"Error: File not found at {docx_path}")
        print("Tip: Provide the full absolute path if the file is outside the current directory.")
        return 1

    if not docx_path.suffix.lower() == ".docx":
        print(f"Error: File must be a .docx file, got {docx_path.suffix}")
        return 1

    print(f"Reading file: {docx_path}")

    # Read the .docx file as bytes
    with open(docx_path, "rb") as f:
        doc_bytes = f.read()

    print(f"File size: {len(doc_bytes):,} bytes")

    # Create extractor service and convert to markdown
    extractor = ExtractorService()
    print("\nExtracting markdown using ExtractorService...")

    markdown_content = extractor.extract_markdown(doc_bytes)

    # Print some stats
    lines = markdown_content.split("\n")
    print(f"\nExtraction complete!")
    print(f"Lines extracted: {len(lines):,}")
    print(f"Characters: {len(markdown_content):,}")
    print(f"Tables found: {markdown_content.count('| --- |')}")

    # Determine output path
    if args.output:
        output_path = args.output.resolve()
    else:
        output_path = docx_path.with_suffix(".md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"\nMarkdown saved to: {output_path}")

    # Print first 3000 characters as preview
    print("\n" + "=" * 80)
    print("PREVIEW (first 3000 characters):")
    print("=" * 80)
    print(markdown_content[:3000])
    if len(markdown_content) > 3000:
        print("\n... (truncated)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
