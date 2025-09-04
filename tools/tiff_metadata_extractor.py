#!/usr/bin/env python3
"""
TIFF Metadata Extractor

This script extracts all metadata from TIFF files and displays all available tags.
It's designed to help map TIFF metadata to the FA 4.0 standardized header format.

Dependencies:
- Pillow (PIL): for basic TIFF handling
- tifffile: for advanced TIFF metadata extraction
- exifread: for EXIF data extraction
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import argparse
from datetime import datetime


from PIL import Image
from PIL.ExifTags import TAGS

import tifffile

import exifread


class TIFFMetadataExtractor:
    """Extract comprehensive metadata from TIFF files"""

    def __init__(self):
        self.all_tags = set()
        self.extracted_data = {}

    def extract_with_pillow(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata using Pillow (PIL)"""

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

                # EXIF data
                if hasattr(img, "_getexif"):
                    exif_data = img._getexif()
                    if exif_data:
                        metadata["exif"] = {}
                        for tag_id, value in exif_data.items():
                            tag_name = TAGS.get(tag_id, tag_id)
                            metadata["exif"][str(tag_name)] = str(value)
                            self.all_tags.add(f"EXIF.{tag_name}")

                # Tag data
                if hasattr(img, "tag_v2"):
                    metadata["tags_v2"] = {}
                    for key, value in img.tag_v2.items():
                        tag_name = TAGS.get(key, f"Tag_{key}")
                        metadata["tags_v2"][str(tag_name)] = str(value)
                        self.all_tags.add(f"PIL.{tag_name}")

                # Legacy tag data
                if hasattr(img, "tag"):
                    metadata["tags"] = {}
                    for key, value in img.tag.items():
                        tag_name = TAGS.get(key, f"Tag_{key}")
                        metadata["tags"][str(tag_name)] = str(value)
                        self.all_tags.add(f"PIL.{tag_name}")

                # Info dictionary
                if hasattr(img, "info"):
                    metadata["info"] = {}
                    for key, value in img.info.items():
                        metadata["info"][str(key)] = str(value)
                        self.all_tags.add(f"PIL.INFO.{key}")

        except Exception as e:
            metadata["error"] = f"Pillow extraction failed: {str(e)}"

        return metadata

    def extract_with_tifffile(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata using tifffile library"""

        metadata = {}
        try:
            with tifffile.TiffFile(file_path) as tif:
                # File-level metadata
                metadata["file_info"] = {
                    "byteorder": tif.byteorder,
                    "is_bigtiff": tif.is_bigtiff,
                    "is_shaped": tif.is_shaped,
                }

                # Process each page/directory
                metadata["pages"] = []
                for i, page in enumerate(tif.pages):
                    page_data = {
                        "page_index": i,
                        "shape": page.shape,
                        "dtype": str(page.dtype),
                        "compression": str(page.compression),
                        "predictor": getattr(page, "predictor", None),
                        "photometric": str(page.photometric),
                        "planarconfig": str(page.planarconfig),
                        "tags": {},
                    }

                    # Extract all tags from this page
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

                        page_data["tags"][tag_name] = tag_value
                        self.all_tags.add(f"TIFF.{tag_name}")

                    metadata["pages"].append(page_data)

                # Global tags (if any)
                if hasattr(tif, "flags"):
                    metadata["flags"] = str(tif.flags)

        except Exception as e:
            metadata["error"] = f"Tifffile extraction failed: {str(e)}"

        return metadata

    def extract_with_exifread(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata using exifread library"""

        metadata = {}
        try:
            with open(file_path, "rb") as f:
                tags = exifread.process_file(f, details=True)

            metadata["exifread_tags"] = {}
            for key, value in tags.items():
                metadata["exifread_tags"][str(key)] = str(value)
                self.all_tags.add(f"EXIFREAD.{key}")

        except Exception as e:
            metadata["error"] = f"Exifread extraction failed: {str(e)}"

        return metadata

    def extract_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract all metadata from a single TIFF file"""
        file_path = Path(file_path)

        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}

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
        metadata["pillow"] = self.extract_with_pillow(str(file_path))
        metadata["tifffile"] = self.extract_with_tifffile(str(file_path))
        metadata["exifread"] = self.extract_with_exifread(str(file_path))

        self.extracted_data[str(file_path)] = metadata
        return metadata

    def scan_directory(self, directory: str, recursive: bool = True) -> List[str]:
        """Scan directory for TIFF files"""
        tiff_extensions = {".tif", ".tiff", ".TIF", ".TIFF", ".tif32", ".TIF32"}
        tiff_files = []

        directory = Path(directory)
        if not directory.exists():
            print(f"Directory not found: {directory}")
            return []

        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"

        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix in tiff_extensions:
                tiff_files.append(str(file_path))

        return sorted(tiff_files)

    def process_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process multiple TIFF files"""
        results = {}

        print(f"Processing {len(file_paths)} TIFF files...")

        for i, file_path in enumerate(file_paths, 1):
            print(f"[{i}/{len(file_paths)}] Processing: {Path(file_path).name}")
            results[file_path] = self.extract_file_metadata(file_path)

        return results

    def get_all_unique_tags(self) -> List[str]:
        """Get all unique tags found across all processed files"""
        return sorted(list(self.all_tags))

    def generate_tag_summary(self) -> Dict[str, Any]:
        """Generate a summary of all tags found"""
        tags_by_source = {}

        for tag in self.all_tags:
            if "." in tag:
                source, tag_name = tag.split(".", 1)
                if source not in tags_by_source:
                    tags_by_source[source] = []
                tags_by_source[source].append(tag_name)
            else:
                if "UNKNOWN" not in tags_by_source:
                    tags_by_source["UNKNOWN"] = []
                tags_by_source["UNKNOWN"].append(tag)

        # Sort tags within each source
        for source in tags_by_source:
            tags_by_source[source] = sorted(list(set(tags_by_source[source])))

        summary = {
            "total_unique_tags": len(self.all_tags),
            "tags_by_source": tags_by_source,
            "all_tags": self.get_all_unique_tags(),
        }

        return summary

    def save_results(self, output_file: str, include_full_data: bool = True):
        """Save extraction results to JSON file"""
        output_data = {
            "extraction_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_files_processed": len(self.extracted_data),
            },
            "tag_summary": self.generate_tag_summary(),
        }

        if include_full_data:
            output_data["full_metadata"] = self.extracted_data

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"Results saved to: {output_file}")

    def print_tag_summary(self):
        """Print a summary of all found tags to console"""
        summary = self.generate_tag_summary()

        print("\n" + "=" * 60)
        print("TIFF METADATA TAG SUMMARY")
        print("=" * 60)
        print(f"Total unique tags found: {summary['total_unique_tags']}")
        print(f"Files processed: {len(self.extracted_data)}")

        for source, tags in summary["tags_by_source"].items():
            print(f"\n{source} Tags ({len(tags)}):")
            print("-" * 40)
            for tag in tags:
                print(f"  • {tag}")

        print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Extract all metadata from TIFF files for FA 4.0 header mapping"
    )
    parser.add_argument(
        "input_path", help="Path to TIFF file or directory containing TIFF files"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="tiff_metadata_extraction_results.json",
        help="Output JSON file (default: tiff_metadata_extraction_results.json)",
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Recursively scan subdirectories"
    )
    parser.add_argument(
        "--no-full-data",
        action="store_true",
        help="Don't include full metadata in output (only tag summary)",
    )
    parser.add_argument(
        "--tags-only",
        action="store_true",
        help="Only display tag summary, don't save full results",
    )

    args = parser.parse_args()

    extractor = TIFFMetadataExtractor()

    # Determine input files
    input_path = Path(args.input_path)
    if input_path.is_file():
        if input_path.suffix.lower() in {".tif", ".tiff"}:
            file_paths = [str(input_path)]
        else:
            print(f"Error: {input_path} is not a TIFF file")
            return 1
    elif input_path.is_dir():
        file_paths = extractor.scan_directory(str(input_path), args.recursive)
        if not file_paths:
            print(f"No TIFF files found in {input_path}")
            return 1
    else:
        print(f"Error: {input_path} does not exist")
        return 1

    # Process files
    extractor.process_files(file_paths)

    # Display tag summary
    extractor.print_tag_summary()

    # Save results if requested
    if not args.tags_only:
        extractor.save_results(args.output, not args.no_full_data)

    return 0


if __name__ == "__main__":
    exit(main())
