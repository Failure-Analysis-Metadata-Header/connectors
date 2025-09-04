#!/usr/bin/env python3
"""
TIFF to FA 4.0 Header Mapping Tool

This script analyzes TIFF metadata and suggests mappings to the FA 4.0 standardized header format.
It uses the extracted metadata to identify potential matches with the JSON schema fields.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
from dataclasses import dataclass


@dataclass
class MappingCandidate:
    """Represents a potential mapping between TIFF metadata and FA 4.0 header"""

    source_tag: str
    source_value: Any
    target_field: str
    confidence: float
    notes: str = ""


class FA40HeaderMapper:
    """Maps TIFF metadata to FA 4.0 header format"""

    def __init__(self, schema_dir: str = "schema"):
        self.schema_dir = Path(schema_dir)
        self.schemas = self.load_schemas()
        self.field_mappings = self.build_field_mappings()

    def load_schemas(self) -> Dict[str, Any]:
        """Load all JSON schema files"""
        schemas = {}

        schema_files = [
            "General Section.json",
            "Method Specific.json",
            "Tool Specific.json",
            "Customer Section.json",
            "Data Evaluation.json",
            "History.json",
        ]

        for schema_file in schema_files:
            schema_path = self.schema_dir / schema_file
            if schema_path.exists():
                try:
                    with open(schema_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Remove comments (lines starting with //)
                        lines = [
                            line
                            for line in content.split("\n")
                            if not line.strip().startswith("//")
                        ]
                        clean_content = "\n".join(lines)
                        schemas[schema_file] = json.loads(clean_content)
                except Exception as e:
                    print(f"Warning: Could not load {schema_file}: {e}")

        return schemas

    def build_field_mappings(self) -> Dict[str, List[str]]:
        """Build a dictionary of potential field mappings based on common terms"""
        mappings = {
            # Image dimensions
            "width": ["Image Width", "ImageWidth", "image_width", "width"],
            "height": [
                "Image Height",
                "ImageLength",
                "image_height",
                "height",
                "length",
            ],
            "bit_depth": ["Bit Depth", "BitsPerSample", "bit_depth", "bits_per_sample"],
            # File information
            "file_name": ["File Name", "DocumentName", "filename"],
            "file_size": ["File Size", "size"],
            "file_format": ["File Format", "format"],
            # Tool/manufacturer information
            "manufacturer": ["Manufacturer", "Make", "manufacturer", "make"],
            "tool_name": ["Tool Name", "Model", "tool_name", "model"],
            "software": ["Software", "software", "version"],
            "serial_number": ["Serial Number", "serial", "serial_number"],
            # Timing
            "timestamp": [
                "Time Stamp",
                "DateTime",
                "timestamp",
                "date_time",
                "creation_time",
            ],
            # Resolution and scaling
            "x_resolution": ["XResolution", "x_resolution", "pixel_width"],
            "y_resolution": ["YResolution", "y_resolution", "pixel_height"],
            "resolution_unit": ["ResolutionUnit", "resolution_unit"],
            # Image properties
            "compression": ["Compression", "compression"],
            "photometric": ["PhotometricInterpretation", "photometric"],
            "orientation": ["Orientation", "orientation"],
            "samples_per_pixel": ["SamplesPerPixel", "samples_per_pixel"],
            # Microscopy specific
            "magnification": ["magnification", "zoom", "mag"],
            "accelerating_voltage": ["voltage", "accelerating_voltage", "kv"],
            "working_distance": ["working_distance", "wd"],
            "detector": ["detector", "signal"],
            "probe_current": ["current", "probe_current"],
            "emission_current": ["emission_current"],
            # Coordinates
            "stage_x": ["stage_x", "x_position", "x_coord"],
            "stage_y": ["stage_y", "y_position", "y_coord"],
            "stage_z": ["stage_z", "z_position", "z_coord"],
        }

        return mappings

    def find_mapping_candidates(
        self, metadata: Dict[str, Any]
    ) -> List[MappingCandidate]:
        """Find potential mappings between TIFF metadata and FA 4.0 fields"""
        candidates = []

        # Extract all tags from the metadata
        all_tags = {}

        # Process different metadata sources
        for source in ["pillow", "tifffile", "exifread"]:
            if source in metadata:
                source_data = metadata[source]
                self._extract_tags_from_source(source_data, all_tags, source)

        # Find mappings
        for fa_field, possible_tags in self.field_mappings.items():
            for tag_name, tag_value in all_tags.items():
                confidence = self._calculate_confidence(fa_field, tag_name, tag_value)
                if confidence > 0.3:  # Only include reasonably confident matches
                    # Find target field in schema
                    target_field = self._find_target_field(fa_field)
                    if target_field:
                        candidate = MappingCandidate(
                            source_tag=tag_name,
                            source_value=tag_value,
                            target_field=target_field,
                            confidence=confidence,
                            notes=self._generate_notes(fa_field, tag_name, tag_value),
                        )
                        candidates.append(candidate)

        # Sort by confidence
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        return candidates

    def _extract_tags_from_source(
        self, source_data: Dict[str, Any], all_tags: Dict[str, Any], source: str
    ):
        """Extract tags from a specific metadata source"""
        if isinstance(source_data, dict):
            for key, value in source_data.items():
                if isinstance(value, dict):
                    self._extract_tags_from_source(value, all_tags, source)
                else:
                    tag_key = f"{source}.{key}"
                    all_tags[tag_key] = value

    def _calculate_confidence(
        self, fa_field: str, tag_name: str, tag_value: Any
    ) -> float:
        """Calculate confidence score for a potential mapping"""
        confidence = 0.0

        # Check if tag name contains the FA field name
        tag_lower = tag_name.lower()
        fa_lower = fa_field.lower()

        if fa_lower in tag_lower:
            confidence += 0.8

        # Check for partial matches
        fa_words = fa_lower.split("_")
        for word in fa_words:
            if word in tag_lower:
                confidence += 0.3

        # Check specific patterns
        if fa_field == "width" and any(w in tag_lower for w in ["width", "imagewidth"]):
            confidence = max(confidence, 0.9)
        elif fa_field == "height" and any(
            w in tag_lower for w in ["height", "length", "imagelength"]
        ):
            confidence = max(confidence, 0.9)
        elif fa_field == "bit_depth" and "bits" in tag_lower:
            confidence = max(confidence, 0.9)
        elif fa_field == "manufacturer" and "make" in tag_lower:
            confidence = max(confidence, 0.8)
        elif fa_field == "tool_name" and "model" in tag_lower:
            confidence = max(confidence, 0.8)

        # Penalize if value seems inappropriate
        if tag_value and isinstance(tag_value, str):
            if fa_field in ["width", "height", "bit_depth"] and not re.search(
                r"\d", tag_value
            ):
                confidence *= 0.5

        return min(confidence, 1.0)

    def _find_target_field(self, fa_field: str) -> Optional[str]:
        """Find the corresponding field in the FA 4.0 schema"""
        # Map to General Section fields
        field_map = {
            "width": "General Section.Image Width",
            "height": "General Section.Image Height",
            "bit_depth": "General Section.Bit Depth",
            "file_name": "General Section.File Name",
            "file_size": "General Section.File Size",
            "file_format": "General Section.File Format",
            "manufacturer": "General Section.Manufacturer",
            "tool_name": "General Section.Tool Name",
            "software": "General Section.Software",
            "serial_number": "General Section.Serial Number",
            "timestamp": "General Section.Time Stamp",
            "x_resolution": "General Section.Pixel Width",
            "y_resolution": "General Section.Pixel Height",
        }

        return field_map.get(fa_field)

    def _generate_notes(self, fa_field: str, tag_name: str, tag_value: Any) -> str:
        """Generate helpful notes about the mapping"""
        notes = []

        if fa_field in ["width", "height"] and isinstance(tag_value, str):
            notes.append("May need unit conversion")

        if fa_field == "timestamp" and tag_value:
            notes.append("Check date format compliance with ISO8601")

        if "tag_" in tag_name.lower():
            notes.append("Custom/proprietary tag - verify meaning")

        return "; ".join(notes)

    def generate_mapping_report(self, metadata_file: str, output_file: str = None):
        """Generate a comprehensive mapping report"""
        # Load metadata
        with open(metadata_file, "r") as f:
            data = json.load(f)

        report = {
            "metadata_source": metadata_file,
            "mapping_candidates": [],
            "unmapped_tags": [],
            "schema_coverage": {},
            "recommendations": [],
        }

        # Process each file's metadata
        if "full_metadata" in data:
            for file_path, metadata in data["full_metadata"].items():
                candidates = self.find_mapping_candidates(metadata)

                file_report = {
                    "file": file_path,
                    "candidates": [
                        {
                            "source_tag": c.source_tag,
                            "source_value": str(c.source_value)[:100] + "..."
                            if len(str(c.source_value)) > 100
                            else str(c.source_value),
                            "target_field": c.target_field,
                            "confidence": c.confidence,
                            "notes": c.notes,
                        }
                        for c in candidates
                    ],
                }
                report["mapping_candidates"].append(file_report)

        # Add recommendations
        report["recommendations"] = [
            "Review high-confidence mappings (>0.8) first",
            "Verify custom tags (32000-32999 range) against manufacturer documentation",
            "Consider creating tool-specific mappings for proprietary metadata",
            "Test timestamp format conversion to ISO8601",
            "Validate unit conversions for measurements",
        ]

        # Save report
        if output_file:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            print(f"Mapping report saved to: {output_file}")

        return report

    def print_summary(self, report: Dict[str, Any]):
        """Print a summary of the mapping analysis"""
        print("\n" + "=" * 60)
        print("FA 4.0 HEADER MAPPING ANALYSIS")
        print("=" * 60)

        total_candidates = sum(
            len(f["candidates"]) for f in report["mapping_candidates"]
        )
        print(f"Total mapping candidates found: {total_candidates}")

        if report["mapping_candidates"]:
            print(f"Files analyzed: {len(report['mapping_candidates'])}")

            # Show top mappings
            print("\nTop mapping candidates:")
            print("-" * 40)

            all_candidates = []
            for file_report in report["mapping_candidates"]:
                all_candidates.extend(file_report["candidates"])

            # Sort by confidence and show top 10
            all_candidates.sort(key=lambda x: x["confidence"], reverse=True)

            for i, candidate in enumerate(all_candidates[:10], 1):
                print(
                    f"{i:2d}. {candidate['source_tag']} -> {candidate['target_field']}"
                )
                print(f"    Confidence: {candidate['confidence']:.2f}")
                print(f"    Value: {candidate['source_value']}")
                if candidate["notes"]:
                    print(f"    Notes: {candidate['notes']}")
                print()

        print("Recommendations:")
        print("-" * 20)
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"{i}. {rec}")

        print("\n" + "=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Map TIFF metadata to FA 4.0 header format"
    )
    parser.add_argument("metadata_file", help="JSON file with extracted TIFF metadata")
    parser.add_argument(
        "-s",
        "--schema-dir",
        default="schema",
        help="Directory containing FA 4.0 schema files (default: schema)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file for mapping report (default: print to console)",
    )

    args = parser.parse_args()

    # Create mapper
    mapper = FA40HeaderMapper(args.schema_dir)

    # Generate mapping report
    report = mapper.generate_mapping_report(args.metadata_file, args.output)

    # Print summary
    mapper.print_summary(report)


if __name__ == "__main__":
    main()
