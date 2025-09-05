#!/usr/bin/env python3
"""
Connector Generator Tool

This tool analyzes TIFF metadata and generates a basic connector JSON file
that maps the available metadata fields to FA 4.0 standard fields.

Usage:
    python connector_generator.py <tiff_file> [output_connector.json]
    python connector_generator.py --from-metadata <metadata.json> [output_connector.json]

The generated connector provides a starting point that can be customized further.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from fa_header_generator import MetadataExtractor


class ConnectorGenerator:
    """Generate basic connector files from TIFF metadata"""

    def __init__(self):
        self.extractor = MetadataExtractor()

        # Common FA 4.0 field mappings with likely source paths
        self.fa40_field_mappings = {
            "File Name": {
                "sources": ["filename"],
                "extraction": "file_metadata",
                "required": True,
                "unit": None,
                "transformation": None,
            },
            "File Size": {
                "sources": ["file_size"],
                "extraction": "file_metadata",
                "required": True,
                "unit": "bytes",
                "transformation": None,
            },
            "Image Width": {
                "sources": [
                    "pillow.width",
                    "pillow.tags_v2.ImageWidth",
                    "tifffile.shape.0",
                ],
                "extraction": "first_available_numeric",
                "required": True,
                "unit": "pixels",
                "transformation": None,
            },
            "Image Height": {
                "sources": [
                    "pillow.height",
                    "pillow.tags_v2.ImageLength",
                    "tifffile.shape.1",
                ],
                "extraction": "first_available_numeric",
                "required": True,
                "unit": "pixels",
                "transformation": None,
            },
            "Bit Depth": {
                "sources": [
                    "pillow.tags_v2.BitsPerSample",
                    "tifffile.tags.BitsPerSample",
                ],
                "extraction": "first_available_numeric",
                "required": False,
                "unit": "bits",
                "transformation": None,
            },
            "Pixel Width": {
                "sources": ["pillow.tags_v2.XResolution", "tifffile.tags.XResolution"],
                "extraction": "first_available_numeric",
                "required": False,
                "unit": "nm",
                "transformation": "resolution_to_pixel_size",
            },
            "Pixel Height": {
                "sources": ["pillow.tags_v2.YResolution", "tifffile.tags.YResolution"],
                "extraction": "first_available_numeric",
                "required": False,
                "unit": "nm",
                "transformation": "resolution_to_pixel_size",
            },
            "Color Mode": {
                "sources": ["pillow.mode", "pillow.basic_info.mode"],
                "extraction": "first_available_string",
                "required": False,
                "unit": None,
                "transformation": "normalize_color_mode",
            },
            "Manufacturer": {
                "sources": ["pillow.tags_v2.Make", "exifread.Image Make"],
                "extraction": "first_available_string",
                "required": False,
                "unit": None,
                "transformation": "clean_string",
            },
            "Tool Name": {
                "sources": ["pillow.tags_v2.Model", "exifread.Image Model"],
                "extraction": "first_available_string",
                "required": False,
                "unit": None,
                "transformation": "clean_string",
            },
            "Software": {
                "sources": [
                    "pillow.tags_v2.Software",
                    "tifffile.software",
                    "exifread.Image Software",
                ],
                "extraction": "first_available_string",
                "required": False,
                "unit": None,
                "transformation": "clean_string",
            },
            "Time Stamp": {
                "sources": [
                    "pillow.tags_v2.DateTime",
                    "tifffile.tags.DateTime",
                    "exifread.Image DateTime",
                ],
                "extraction": "first_available_string",
                "required": False,
                "unit": None,
                "transformation": "datetime_to_iso8601",
            },
        }

    def analyze_metadata(self, metadata: Dict[str, Any]) -> Dict[str, List[str]]:
        """Analyze metadata to find available fields and suggest mappings"""

        def collect_paths(obj, prefix=""):
            """Recursively collect all available paths in metadata"""
            paths = []
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{prefix}.{key}" if prefix else str(key)
                    paths.append(current_path)
                    if isinstance(value, (dict, list)):
                        paths.extend(collect_paths(value, current_path))
            elif isinstance(obj, list) and obj:
                # For lists, just note the path with index notation
                current_path = f"{prefix}.0" if prefix else "0"
                paths.append(current_path)
                if isinstance(obj[0], (dict, list)):
                    paths.extend(collect_paths(obj[0], current_path))
            return paths

        # Collect all available paths
        all_paths = collect_paths(metadata)

        # Group paths by category
        categories = {
            "file_metadata": [p for p in all_paths if "." not in p],
            "pillow": [p for p in all_paths if p.startswith("pillow.")],
            "tifffile": [p for p in all_paths if p.startswith("tifffile.")],
            "exifread": [p for p in all_paths if p.startswith("exifread.")],
            "custom": [
                p for p in all_paths if any(str(i) in p for i in range(32000, 33000))
            ],
        }

        return categories

    def find_matching_sources(
        self, metadata: Dict[str, Any], field_name: str, suggested_sources: List[str]
    ) -> List[str]:
        """Find which suggested sources actually exist in the metadata"""
        existing_sources = []

        for source in suggested_sources:
            if self._path_exists_in_metadata(metadata, source):
                existing_sources.append(source)

        return existing_sources

    def _path_exists_in_metadata(self, metadata: Dict[str, Any], path: str) -> bool:
        """Check if a specific path exists in the metadata"""
        try:
            parts = path.split(".")
            current = metadata

            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                elif (
                    isinstance(current, list)
                    and part.isdigit()
                    and int(part) < len(current)
                ):
                    current = current[int(part)]
                else:
                    return False
            return True
        except Exception as e:
            print(f"Error checking path '{path}': {e}")
            return False

    def suggest_custom_fields(self, metadata: Dict[str, Any]) -> Dict[str, Dict]:
        """Suggest custom field mappings based on available metadata"""
        custom_fields = {}

        # Look for custom tags (32000-32999 range)
        if "pillow" in metadata and "tags_v2" in metadata["pillow"]:
            for tag, value in metadata["pillow"]["tags_v2"].items():
                if isinstance(tag, int) and 32000 <= tag <= 32999:
                    field_name = f"Custom Tag {tag}"
                    custom_fields[field_name] = {
                        "source": [f"pillow.tags_v2.{tag}"],
                        "extraction": "first_available_string",
                        "required": False,
                        "transformation": "clean_string",
                        "description": f"Custom tag {tag} from source equipment",
                    }

        # Look for other interesting fields
        interesting_patterns = [
            ("wafer", "Wafer ID"),
            ("sample", "Sample ID"),
            ("lot", "Lot Number"),
            ("recipe", "Recipe Name"),
            ("process", "Process Name"),
            ("operator", "Operator"),
            ("temperature", "Temperature"),
            ("pressure", "Pressure"),
        ]

        all_paths = self._get_all_paths(metadata)
        for pattern, field_name in interesting_patterns:
            matching_paths = [p for p in all_paths if pattern.lower() in p.lower()]
            if matching_paths:
                custom_fields[field_name] = {
                    "source": matching_paths[:3],  # Take first 3 matches
                    "extraction": "first_available_string",
                    "required": False,
                    "transformation": "clean_string",
                    "description": f"Auto-detected field containing '{pattern}'",
                }

        return custom_fields

    def _get_all_paths(self, obj, prefix=""):
        """Get all paths in a nested structure"""
        paths = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{prefix}.{key}" if prefix else str(key)
                paths.append(current_path)
                if isinstance(value, (dict, list)):
                    paths.extend(self._get_all_paths(value, current_path))
        elif isinstance(obj, list) and obj:
            for i, item in enumerate(obj[:3]):  # Check first 3 items
                current_path = f"{prefix}.{i}" if prefix else str(i)
                paths.append(current_path)
                if isinstance(item, (dict, list)):
                    paths.extend(self._get_all_paths(item, current_path))
        return paths

    def generate_connector(
        self, metadata: Dict[str, Any], connector_name: str = "Auto-generated Connector"
    ) -> Dict[str, Any]:
        """Generate a complete connector configuration from metadata"""

        # Analyze available metadata
        available_categories = self.analyze_metadata(metadata)

        # Build connector structure
        connector = {
            "metadata": {
                "name": connector_name,
                "version": "1.0.0",
                "description": f"Auto-generated connector created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "target_format": "FA4.0",
                "source_type": "TIFF",
                "auto_generated": True,
            },
            "mappings": {
                "general_section": {},
                "tool_specific": {},
                "method_specific": {},
                "customer_specific": {},
            },
            "validation": {"required_fields": [], "optional_fields": []},
        }

        # Map general section fields
        for field_name, field_config in self.fa40_field_mappings.items():
            existing_sources = self.find_matching_sources(
                metadata, field_name, field_config["sources"]
            )

            if existing_sources:
                # Build field configuration
                field_def = {
                    "source": existing_sources,
                    "extraction": field_config["extraction"],
                    "required": field_config["required"],
                }

                if field_config["unit"]:
                    field_def["unit"] = field_config["unit"]

                if field_config["transformation"]:
                    field_def["transformation"] = field_config["transformation"]

                field_def["description"] = (
                    f"Auto-mapped from available sources: {', '.join(existing_sources[:2])}"
                )

                connector["mappings"]["general_section"][field_name] = field_def

                # Add to validation lists
                validation_key = f"general_section.{field_name}"
                if field_config["required"]:
                    connector["validation"]["required_fields"].append(validation_key)
                else:
                    connector["validation"]["optional_fields"].append(validation_key)

        # Add custom/tool-specific fields
        custom_fields = self.suggest_custom_fields(metadata)
        for field_name, field_config in custom_fields.items():
            connector["mappings"]["tool_specific"][field_name] = field_config
            connector["validation"]["optional_fields"].append(
                f"tool_specific.{field_name}"
            )

        # Add metadata statistics
        connector["metadata"]["analysis"] = {
            "total_fields_found": len(self._get_all_paths(metadata)),
            "mapped_general_fields": len(connector["mappings"]["general_section"]),
            "mapped_tool_fields": len(connector["mappings"]["tool_specific"]),
            "available_categories": {
                k: len(v) for k, v in available_categories.items()
            },
            "coverage_percentage": round(
                len(connector["mappings"]["general_section"])
                / len(self.fa40_field_mappings)
                * 100,
                1,
            ),
        }

        return connector

    def generate_from_tiff(
        self, tiff_file: str, connector_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate connector from TIFF file"""
        if not Path(tiff_file).exists():
            raise FileNotFoundError(f"TIFF file not found: {tiff_file}")

        print(f"Extracting metadata from: {Path(tiff_file).name}")
        metadata = self.extractor.extract_file_metadata(tiff_file)

        if not connector_name:
            connector_name = f"Connector for {Path(tiff_file).stem}"

        return self.generate_connector(metadata, connector_name)

    def generate_from_metadata_file(
        self, metadata_file: str, connector_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate connector from metadata JSON file"""
        if not Path(metadata_file).exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        if not connector_name:
            connector_name = f"Connector from {Path(metadata_file).stem}"

        return self.generate_connector(metadata, connector_name)

    def save_connector(self, connector: Dict[str, Any], output_file: str):
        """Save connector to JSON file"""
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(connector, f, indent=2, ensure_ascii=False)
        print(f"Connector saved to: {output_file}")


def main():
    """Main command line interface"""
    parser = argparse.ArgumentParser(
        description="Generate FA 4.0 connector files from TIFF metadata"
    )
    parser.add_argument("input", help="Input TIFF file or metadata JSON file")
    parser.add_argument(
        "output",
        nargs="?",
        help="Output connector JSON file (default: auto-generated name)",
    )
    parser.add_argument(
        "--from-metadata",
        action="store_true",
        help="Input is metadata JSON file instead of TIFF",
    )
    parser.add_argument("--name", help="Custom name for the connector")
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze metadata without generating connector",
    )

    args = parser.parse_args()

    try:
        generator = ConnectorGenerator()

        # Generate output filename if not provided
        if not args.output:
            input_stem = Path(args.input).stem
            args.output = f"{input_stem}_connector.json"

        # Generate connector
        if args.from_metadata:
            connector = generator.generate_from_metadata_file(args.input, args.name)
        else:
            connector = generator.generate_from_tiff(args.input, args.name)

        # Print analysis summary
        analysis = connector["metadata"]["analysis"]
        print(f"\n📊 Analysis Summary:")
        print(f"  Total metadata fields found: {analysis['total_fields_found']}")
        print(f"  Mapped general fields: {analysis['mapped_general_fields']}")
        print(f"  Mapped tool-specific fields: {analysis['mapped_tool_fields']}")
        print(f"  Coverage of FA 4.0 standard: {analysis['coverage_percentage']}%")
        print(
            f"  Available categories: {', '.join(analysis['available_categories'].keys())}"
        )

        if args.analyze_only:
            print(
                f"\n🔍 Analysis complete. Use without --analyze-only to generate connector file."
            )
            return

        # Save connector
        generator.save_connector(connector, args.output)

        print(f"\n✅ Connector generation complete!")
        print(f"📁 Output: {args.output}")
        print(f"🎯 Next steps:")
        print(f"   1. Review and customize the generated mappings")
        print(
            f"   2. Test with: python fa_header_generator.py {args.input} {args.output}"
        )
        print(f"   3. Refine field mappings and transformations as needed")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
