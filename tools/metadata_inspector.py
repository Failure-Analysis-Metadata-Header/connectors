#!/usr/bin/env python3
"""
TIFF Metadata Inspector

A utility to inspect specific TIFF metadata values and understand their structure.
This helps in creating accurate connector mappings.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import argparse


class MetadataInspector:
    """Inspect and analyze specific metadata values"""

    def __init__(self, metadata_file: str):
        with open(metadata_file, "r") as f:
            self.data = json.load(f)

    def list_files(self) -> List[str]:
        """List all files in the metadata"""
        if "full_metadata" in self.data:
            return list(self.data["full_metadata"].keys())
        return []

    def inspect_tag(self, tag_pattern: str, file_index: int = 0) -> Dict[str, Any]:
        """Inspect a specific tag across all sources"""
        files = self.list_files()
        if not files or file_index >= len(files):
            return {"error": "No files or invalid file index"}

        file_path = files[file_index]
        metadata = self.data["full_metadata"][file_path]

        results = {}
        tag_pattern_lower = tag_pattern.lower()

        # Search in all metadata sources
        for source in ["pillow", "tifffile", "exifread"]:
            if source in metadata:
                source_results = self._search_in_source(
                    metadata[source], tag_pattern_lower
                )
                if source_results:
                    results[source] = source_results

        return {"file": file_path, "tag_pattern": tag_pattern, "matches": results}

    def _search_in_source(
        self, data: Any, pattern: str, prefix: str = ""
    ) -> Dict[str, Any]:
        """Recursively search for tags matching pattern"""
        results = {}

        if isinstance(data, dict):
            for key, value in data.items():
                current_key = f"{prefix}.{key}" if prefix else key

                if pattern in key.lower():
                    results[current_key] = {
                        "value": value,
                        "type": type(value).__name__,
                        "length": len(str(value)) if value is not None else 0,
                    }

                # Recursively search nested dictionaries
                if isinstance(value, dict):
                    nested_results = self._search_in_source(value, pattern, current_key)
                    results.update(nested_results)

        return results

    def get_custom_tags(self, file_index: int = 0) -> Dict[str, Any]:
        """Get all custom tags (32000-32999 range)"""
        files = self.list_files()
        if not files or file_index >= len(files):
            return {"error": "No files or invalid file index"}

        file_path = files[file_index]
        metadata = self.data["full_metadata"][file_path]

        custom_tags = {}

        # Look in all sources
        for source in ["pillow", "tifffile", "exifread"]:
            if source in metadata:
                source_custom = self._find_custom_tags(metadata[source])
                if source_custom:
                    custom_tags[source] = source_custom

        return {"file": file_path, "custom_tags": custom_tags}

    def _find_custom_tags(self, data: Any, prefix: str = "") -> Dict[str, Any]:
        """Find custom TIFF tags (32000-32999)"""
        results = {}

        if isinstance(data, dict):
            for key, value in data.items():
                current_key = f"{prefix}.{key}" if prefix else key

                # Check if key is a custom tag number
                if key.startswith("Tag_32") or (key.startswith("32") and key.isdigit()):
                    tag_num = int(key.replace("Tag_", ""))
                    if 32000 <= tag_num <= 32999:
                        results[current_key] = {
                            "tag_number": tag_num,
                            "value": value,
                            "type": type(value).__name__,
                            "value_preview": str(value)[:100] + "..."
                            if len(str(value)) > 100
                            else str(value),
                        }

                # Also check in nested dictionaries
                if isinstance(value, dict):
                    nested_results = self._find_custom_tags(value, current_key)
                    results.update(nested_results)

        return results

    def compare_files(self, tag_name: str) -> Dict[str, Any]:
        """Compare a specific tag across all files"""
        files = self.list_files()
        comparison = {}

        for file_path in files:
            metadata = self.data["full_metadata"][file_path]
            file_name = Path(file_path).name

            tag_values = {}
            for source in ["pillow", "tifffile", "exifread"]:
                if source in metadata:
                    matches = self._search_in_source(metadata[source], tag_name.lower())
                    if matches:
                        tag_values[source] = matches

            if tag_values:
                comparison[file_name] = tag_values

        return {"tag_name": tag_name, "comparison": comparison}

    def print_tag_info(self, tag_pattern: str, file_index: int = 0):
        """Print detailed information about a tag"""
        result = self.inspect_tag(tag_pattern, file_index)

        print(f"\n{'=' * 60}")
        print(f"TAG INSPECTION: {tag_pattern}")
        print(f"{'=' * 60}")
        print(f"File: {Path(result['file']).name}")

        if "matches" in result and result["matches"]:
            for source, matches in result["matches"].items():
                print(f"\n{source.upper()} source:")
                print("-" * 30)
                for tag_key, info in matches.items():
                    print(f"  Tag: {tag_key}")
                    print(f"  Type: {info['type']}")
                    print(f"  Length: {info['length']}")
                    print(f"  Value: {info['value']}")
                    print()
        else:
            print("No matches found.")

    def print_custom_tags(self, file_index: int = 0):
        """Print all custom tags"""
        result = self.get_custom_tags(file_index)

        print(f"\n{'=' * 60}")
        print("CUSTOM TAGS (32000-32999)")
        print(f"{'=' * 60}")
        print(f"File: {Path(result['file']).name}")

        if "custom_tags" in result and result["custom_tags"]:
            for source, tags in result["custom_tags"].items():
                print(f"\n{source.upper()} source:")
                print("-" * 30)
                for tag_key, info in tags.items():
                    print(f"  Tag {info['tag_number']}: {tag_key}")
                    print(f"  Type: {info['type']}")
                    print(f"  Value: {info['value_preview']}")
                    print()
        else:
            print("No custom tags found.")


def main():
    parser = argparse.ArgumentParser(description="Inspect TIFF metadata values")
    parser.add_argument("metadata_file", help="JSON file with extracted TIFF metadata")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List files command
    subparsers.add_parser("list", help="List all files in metadata")

    # Inspect tag command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a specific tag")
    inspect_parser.add_argument("tag_pattern", help="Tag name pattern to search for")
    inspect_parser.add_argument(
        "-f",
        "--file-index",
        type=int,
        default=0,
        help="File index to inspect (default: 0)",
    )

    # Custom tags command
    custom_parser = subparsers.add_parser(
        "custom", help="Show custom tags (32000-32999)"
    )
    custom_parser.add_argument(
        "-f",
        "--file-index",
        type=int,
        default=0,
        help="File index to inspect (default: 0)",
    )

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare tag across files")
    compare_parser.add_argument("tag_name", help="Tag name to compare")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    inspector = MetadataInspector(args.metadata_file)

    if args.command == "list":
        files = inspector.list_files()
        print(f"Found {len(files)} files:")
        for i, file_path in enumerate(files):
            print(f"  {i}: {Path(file_path).name}")

    elif args.command == "inspect":
        inspector.print_tag_info(args.tag_pattern, args.file_index)

    elif args.command == "custom":
        inspector.print_custom_tags(args.file_index)

    elif args.command == "compare":
        result = inspector.compare_files(args.tag_name)
        print(f"\n{'=' * 60}")
        print(f"COMPARING TAG: {result['tag_name']}")
        print(f"{'=' * 60}")

        for file_name, sources in result["comparison"].items():
            print(f"\nFile: {file_name}")
            print("-" * 30)
            for source, matches in sources.items():
                print(f"  {source}:")
                for tag_key, info in matches.items():
                    print(f"    {tag_key}: {info['value']}")


if __name__ == "__main__":
    main()
