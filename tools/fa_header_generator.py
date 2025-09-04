#!/usr/bin/env python3
"""
FA 4.0 Header Generator

This module creates FA 4.0 standardized JSON headers from TIFF files using connector mappings.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import argparse

# Check for optional dependencies
try:
    from PIL import Image
    from PIL.ExifTags import TAGS

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import tifffile

    TIFFFILE_AVAILABLE = True
except ImportError:
    TIFFFILE_AVAILABLE = False

try:
    import exifread

    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False


class SimpleTIFFMetadataExtractor:
    """Simplified TIFF metadata extractor for FA 4.0 header generation"""

    def extract_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from a TIFF file"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "modified_time": datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).isoformat(),
            "extraction_timestamp": datetime.now().isoformat(),
        }

        # Extract using different libraries
        metadata["pillow"] = self._extract_with_pillow(str(file_path))
        metadata["tifffile"] = self._extract_with_tifffile(str(file_path))
        metadata["exifread"] = self._extract_with_exifread(str(file_path))

        return metadata

    def _extract_with_pillow(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata using Pillow (PIL)"""
        if not PIL_AVAILABLE:
            return {}

        metadata = {}
        try:
            with Image.open(file_path) as img:
                # Basic image info
                metadata["basic_info"] = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height,
                }

                # Tag data
                if hasattr(img, "tag_v2"):
                    metadata["tags_v2"] = {}
                    for key, value in img.tag_v2.items():
                        tag_name = TAGS.get(key, f"Tag_{key}")
                        metadata["tags_v2"][tag_name] = value

        except Exception as e:
            metadata["error"] = f"Pillow extraction failed: {str(e)}"

        return metadata

    def _extract_with_tifffile(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata using tifffile library"""
        if not TIFFFILE_AVAILABLE:
            return {}

        metadata = {}
        try:
            with tifffile.TiffFile(file_path) as tif:
                # Process first page only for simplicity
                if tif.pages:
                    page = tif.pages[0]
                    metadata["pages"] = [
                        {"shape": page.shape, "dtype": str(page.dtype), "tags": {}}
                    ]

                    # Extract tags from first page
                    for tag in page.tags:
                        tag_name = tag.name
                        tag_value = tag.value

                        # Convert complex types to strings for JSON serialization
                        if hasattr(tag_value, "tolist"):
                            tag_value = tag_value.tolist()
                        elif not isinstance(
                            tag_value, (str, int, float, bool, type(None))
                        ):
                            tag_value = str(tag_value)

                        metadata["pages"][0]["tags"][tag_name] = tag_value

        except Exception as e:
            metadata["error"] = f"Tifffile extraction failed: {str(e)}"

        return metadata

    def _extract_with_exifread(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata using exifread library"""
        if not EXIFREAD_AVAILABLE:
            return {}

        metadata = {}
        try:
            with open(file_path, "rb") as f:
                tags = exifread.process_file(f, details=True)

            metadata["exifread_tags"] = {}
            for key, value in tags.items():
                metadata["exifread_tags"][str(key)] = str(value)

        except Exception as e:
            metadata["error"] = f"Exifread extraction failed: {str(e)}"

        return metadata


class FA40HeaderGenerator:
    """Generate FA 4.0 standardized headers from TIFF files using connector mappings"""

    def __init__(self, connector_file: str):
        """Initialize with a connector file"""
        self.connector = self.load_connector(connector_file)
        self.metadata_extractor = SimpleTIFFMetadataExtractor()

    def load_connector(self, connector_file: str) -> Dict[str, Any]:
        """Load connector mapping configuration"""
        with open(connector_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def extract_tiff_metadata(self, tiff_file: str) -> Dict[str, Any]:
        """Extract metadata from TIFF file"""
        return self.metadata_extractor.extract_file_metadata(tiff_file)

    def apply_transformation(self, value: Any, transformation: str) -> Any:
        """Apply transformation function to a value"""
        if transformation == "clean_string":
            return self._clean_string(value)
        elif transformation == "first_available_numeric":
            return self._parse_first_number(value)
        elif transformation == "first_available_string":
            return self._get_first_valid_string(value)
        elif transformation == "convert_to_iso8601":
            return self._datetime_to_iso8601(value)
        elif transformation == "dpi_to_nanometers":
            return self._resolution_to_pixel_size(value)
        elif transformation == "standardize_color_mode":
            return self._normalize_color_mode(value)
        else:
            return value

    def _clean_string(self, value: Any) -> str:
        """Remove null bytes and control characters"""
        if isinstance(value, tuple) and len(value) > 0:
            value = value[0]
        if isinstance(value, str):
            # Remove null bytes and control characters
            cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", value)
            return cleaned.strip()
        return str(value) if value is not None else ""

    def _parse_first_number(self, value: Any) -> Optional[Union[int, float]]:
        """Extract first numeric value from various formats"""
        if isinstance(value, (int, float)):
            return value
        elif isinstance(value, tuple) and len(value) > 0:
            if isinstance(value[0], (int, float)):
                return value[0]
            value = value[0]
        elif isinstance(value, list) and len(value) > 0:
            if isinstance(value[0], (int, float)):
                return value[0]
            value = value[0]

        if isinstance(value, str):
            # Try to extract number from string
            numbers = re.findall(r"-?\d+\.?\d*", value)
            if numbers:
                try:
                    return float(numbers[0]) if "." in numbers[0] else int(numbers[0])
                except ValueError:
                    pass

        return None

    def _get_first_valid_string(self, value: Any) -> str:
        """Get first valid string from various formats"""
        if isinstance(value, tuple) and len(value) > 0:
            value = value[0]
        elif isinstance(value, list) and len(value) > 0:
            value = value[0]

        if isinstance(value, str):
            return self._clean_string(value)

        return str(value) if value is not None else ""

    def _datetime_to_iso8601(self, value: Any) -> Optional[str]:
        """Convert various datetime formats to ISO8601"""
        if not value:
            return None

        value_str = self._get_first_valid_string(value)
        if not value_str:
            return None

        # Common TIFF datetime format: "YYYY:MM:DD HH:MM:SS"
        try:
            if ":" in value_str and " " in value_str:
                dt = datetime.strptime(value_str, "%Y:%m:%d %H:%M:%S")
                return dt.isoformat()
        except ValueError:
            pass

        # Try other common formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%Y:%m:%d",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(value_str, fmt)
                return dt.isoformat()
            except ValueError:
                continue

        return value_str  # Return as-is if can't parse

    def _resolution_to_pixel_size(self, value: Any) -> Optional[float]:
        """Convert resolution (DPI) to pixel size in nanometers"""
        dpi = self._parse_first_number(value)
        if dpi and dpi > 0:
            # Convert DPI to nanometers per pixel
            # 1 inch = 25.4 mm = 25,400,000 nm
            nm_per_pixel = 25400000 / dpi
            return round(nm_per_pixel, 2)
        return None

    def _normalize_color_mode(self, value: Any) -> str:
        """Normalize color mode representations"""
        mode_str = self._get_first_valid_string(value).lower()

        mode_map = {
            "l": "grayscale",
            "grayscale": "grayscale",
            "grey": "grayscale",
            "gray": "grayscale",
            "rgb": "rgb",
            "rgba": "rgb",
            "cmyk": "cmyk",
            "palette": "palette",
            "p": "palette",
        }

        return mode_map.get(mode_str, mode_str)

    def extract_value_from_source(
        self, metadata: Dict[str, Any], source_path: str
    ) -> Any:
        """Extract value from metadata using dot notation path"""
        parts = source_path.split(".")
        current = metadata

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def resolve_field_value(
        self, metadata: Dict[str, Any], field_config: Dict[str, Any]
    ) -> Any:
        """Resolve field value using connector configuration"""
        sources = field_config.get("source", [])
        if isinstance(sources, str):
            sources = [sources]

        # Try each source until we find a value
        for source in sources:
            if source == "filename":
                value = Path(metadata["file_path"]).name
            elif source == "file_size":
                value = metadata["file_size"]
            elif source == "format":
                value = metadata.get("pillow", {}).get("basic_info", {}).get("format")
            else:
                value = self.extract_value_from_source(metadata, source)

            if value is not None:
                # Apply transformation if specified
                transformation = field_config.get("transformation")
                if transformation:
                    value = self.apply_transformation(value, transformation)

                # Apply extraction method
                extraction = field_config.get("extraction", "as_is")
                if extraction == "first_available_numeric":
                    value = self._parse_first_number(value)
                elif extraction == "first_available_string":
                    value = self._get_first_valid_string(value)
                elif extraction in ["resolution_to_pixel_size", "dpi_to_nanometers"]:
                    value = self._resolution_to_pixel_size(value)

                if value is not None:
                    return value

        return None

    def generate_fa40_header(
        self, tiff_file: str, output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate FA 4.0 header from TIFF file using connector"""

        # Extract metadata from TIFF
        print(f"Extracting metadata from: {Path(tiff_file).name}")
        metadata = self.extract_tiff_metadata(tiff_file)

        # Initialize FA 4.0 header structure
        fa40_header = {
            "General Section": {},
            "Method Specific": {},
            "Tool Specific": {},
            "Customer Specific": {},
            "Data Evaluation": {},
            "History": {},
        }

        # Process mappings from connector
        if "mappings" in self.connector:
            for section_name, section_mappings in self.connector["mappings"].items():
                if section_name == "general_section":
                    target_section = "General Section"
                elif section_name == "method_specific":
                    target_section = "Method Specific"
                elif section_name == "tool_specific":
                    target_section = "Tool Specific"
                else:
                    continue

                for field_name, field_config in section_mappings.items():
                    value = self.resolve_field_value(metadata, field_config)

                    if value is not None:
                        # Create value object with unit if specified
                        unit = field_config.get("unit")
                        if unit and field_name in [
                            "Image Width",
                            "Image Height",
                            "File Size",
                            "Pixel Width",
                            "Pixel Height",
                        ]:
                            fa40_header[target_section][field_name] = {
                                "Value": value,
                                "Unit": unit,
                            }
                        else:
                            fa40_header[target_section][field_name] = value

        # Add header metadata
        fa40_header["General Section"]["Header Type"] = "FA4.0 standardized header"
        fa40_header["General Section"]["Version"] = "v1.0"
        fa40_header["General Section"]["Time Stamp"] = datetime.now().isoformat()

        # Add file path if not already present
        if "File Path" not in fa40_header["General Section"]:
            fa40_header["General Section"]["File Path"] = str(Path(tiff_file).parent)

        # Save to file if specified
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(fa40_header, f, indent=2, ensure_ascii=False)
            print(f"FA 4.0 header saved to: {output_file}")

        return fa40_header

    def validate_header(self, header: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate generated header against connector requirements"""
        validation_results = {
            "missing_required": [],
            "present_optional": [],
            "validation_errors": [],
        }

        if "validation" in self.connector:
            required_fields = self.connector["validation"].get("required_fields", [])
            optional_fields = self.connector["validation"].get("optional_fields", [])

            # Check required fields
            for field_path in required_fields:
                section, field = field_path.split(".", 1)
                section_map = {
                    "general_section": "General Section",
                    "method_specific": "Method Specific",
                    "tool_specific": "Tool Specific",
                }
                actual_section = section_map.get(section, section)

                if actual_section not in header or field not in header[actual_section]:
                    validation_results["missing_required"].append(field_path)

            # Check optional fields
            for field_path in optional_fields:
                section, field = field_path.split(".", 1)
                section_map = {
                    "general_section": "General Section",
                    "method_specific": "Method Specific",
                    "tool_specific": "Tool Specific",
                }
                actual_section = section_map.get(section, section)

                if actual_section in header and field in header[actual_section]:
                    validation_results["present_optional"].append(field_path)

        return validation_results

    def print_validation_report(self, validation: Dict[str, List[str]]):
        """Print validation report"""
        print("\n" + "=" * 60)
        print("FA 4.0 HEADER VALIDATION REPORT")
        print("=" * 60)

        if validation["missing_required"]:
            print(
                f"\n❌ Missing Required Fields ({len(validation['missing_required'])}):"
            )
            for field in validation["missing_required"]:
                print(f"   • {field}")
        else:
            print("\n✅ All required fields present")

        if validation["present_optional"]:
            print(
                f"\n✅ Optional Fields Present ({len(validation['present_optional'])}):"
            )
            for field in validation["present_optional"]:
                print(f"   • {field}")

        if validation["validation_errors"]:
            print(f"\n⚠️  Validation Errors ({len(validation['validation_errors'])}):")
            for error in validation["validation_errors"]:
                print(f"   • {error}")

        print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate FA 4.0 headers from TIFF files using connector mappings"
    )
    parser.add_argument("tiff_file", help="Path to TIFF file")
    parser.add_argument("connector_file", help="Path to connector JSON file")
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file (default: <tiff_name>_fa40_header.json)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate generated header against connector requirements",
    )
    parser.add_argument(
        "--pretty-print", action="store_true", help="Print generated header to console"
    )

    args = parser.parse_args()

    # Determine output file
    if args.output:
        output_file = args.output
    else:
        tiff_path = Path(args.tiff_file)
        output_file = tiff_path.stem + "_fa40_header.json"

    # Generate header
    generator = FA40HeaderGenerator(args.connector_file)
    header = generator.generate_fa40_header(args.tiff_file, output_file)

    # Pretty print if requested
    if args.pretty_print:
        print("\nGenerated FA 4.0 Header:")
        print(json.dumps(header, indent=2, ensure_ascii=False))

    # Validate if requested
    if args.validate:
        validation = generator.validate_header(header)
        generator.print_validation_report(validation)

    return header


if __name__ == "__main__":
    main()
