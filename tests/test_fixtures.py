# Test Configuration and Fixtures

import os
import json
import tempfile
from pathlib import Path
from unittest import mock

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"

# Sample TIFF metadata for testing
SAMPLE_TIFF_METADATA = {
    "file_path": "/test/sample.tif",
    "file_name": "sample.tif",
    "file_size": 2048576,
    "modified_time": 1697375425.0,
    "extraction_timestamp": "2023-10-15T14:30:25",
    "pillow": {
        "format": "TIFF",
        "mode": "RGB",
        "width": 1000,
        "height": 1000,
        "bands": 3,
        "basic_info": {"format": "TIFF", "mode": "RGB", "size": [1000, 1000]},
        "tags_v2": {
            "ImageWidth": 1000,
            "ImageLength": 1000,
            "BitsPerSample": (8, 8, 8),
            "Compression": 1,
            "PhotometricInterpretation": 2,
            "Software": "SemiShop\x00Software",
            "DateTime": "2023:10:15 14:30:25",
            "XResolution": (96.0, 1.0),
            "YResolution": (96.0, 1.0),
            "ResolutionUnit": 2,
            32000: "Custom Tool Data",
            32001: "SemiShop v2.1",
            32002: "Wafer_ID_12345",
        },
    },
    "tifffile": {
        "shape": [1000, 1000, 3],
        "dtype": "uint8",
        "photometric": "rgb",
        "compression": "none",
        "description": "",
        "software": "SemiShop Software v2.1",
        "tags": {
            "ImageWidth": 1000,
            "ImageLength": 1000,
            "BitsPerSample": [8, 8, 8],
            "Software": "SemiShop Software v2.1\x00",
            "DateTime": "2023:10:15 14:30:25",
        },
    },
    "exifread": {
        "Image Software": "SemiShop Software v2.1",
        "Image DateTime": "2023:10:15 14:30:25",
        "Image XResolution": "96",
        "Image YResolution": "96",
        "Image ResolutionUnit": "Pixels/Inch",
    },
}

# Sample connector configuration for testing
SAMPLE_CONNECTOR = {
    "metadata": {
        "name": "Test Connector",
        "version": "1.0.0",
        "description": "Test connector for unit testing",
        "target_format": "FA4.0",
        "source_type": "TIFF",
    },
    "mappings": {
        "general_section": {
            "File Name": {
                "source": ["filename"],
                "extraction": "file_metadata",
                "required": True,
                "description": "Name of the source file",
            },
            "File Size": {
                "source": ["file_size"],
                "extraction": "file_metadata",
                "unit": "bytes",
                "required": True,
            },
            "Image Width": {
                "source": [
                    "pillow.width",
                    "pillow.tags_v2.ImageWidth",
                    "tifffile.shape.0",
                ],
                "extraction": "first_available_numeric",
                "unit": "pixels",
                "required": True,
            },
            "Image Height": {
                "source": [
                    "pillow.height",
                    "pillow.tags_v2.ImageLength",
                    "tifffile.shape.1",
                ],
                "extraction": "first_available_numeric",
                "unit": "pixels",
                "required": True,
            },
            "Bit Depth": {
                "source": [
                    "pillow.tags_v2.BitsPerSample",
                    "tifffile.tags.BitsPerSample",
                ],
                "extraction": "first_available_numeric",
                "unit": "bits",
                "required": False,
            },
            "Pixel Width": {
                "source": ["pillow.tags_v2.XResolution", "tifffile.tags.XResolution"],
                "extraction": "first_available_numeric",
                "transformation": "resolution_to_pixel_size",
                "unit": "nm",
                "required": False,
            },
            "Color Mode": {
                "source": ["pillow.mode", "pillow.basic_info.mode"],
                "extraction": "first_available_string",
                "transformation": "normalize_color_mode",
                "required": False,
            },
            "Software": {
                "source": [
                    "pillow.tags_v2.Software",
                    "tifffile.software",
                    "exifread.Image Software",
                ],
                "extraction": "first_available_string",
                "transformation": "clean_string",
                "required": False,
            },
            "Time Stamp": {
                "source": [
                    "pillow.tags_v2.DateTime",
                    "tifffile.tags.DateTime",
                    "exifread.Image DateTime",
                ],
                "extraction": "first_available_string",
                "transformation": "datetime_to_iso8601",
                "required": False,
            },
        },
        "tool_specific": {
            "Tool Name": {
                "source": ["pillow.tags_v2.32001", "custom_tool_name"],
                "extraction": "first_available_string",
                "transformation": "clean_string",
                "required": False,
            },
            "Wafer ID": {
                "source": ["pillow.tags_v2.32002", "wafer_identifier"],
                "extraction": "first_available_string",
                "transformation": "clean_string",
                "required": False,
            },
        },
    },
    "validation": {
        "required_fields": [
            "general_section.File Name",
            "general_section.File Size",
            "general_section.Image Width",
            "general_section.Image Height",
        ],
        "optional_fields": [
            "general_section.Bit Depth",
            "general_section.Pixel Width",
            "general_section.Color Mode",
            "general_section.Software",
            "general_section.Time Stamp",
            "tool_specific.Tool Name",
            "tool_specific.Wafer ID",
        ],
    },
}

# Expected FA 4.0 header structure
EXPECTED_FA40_HEADER = {
    "General Section": {
        "Header Type": "FA4.0 standardized header",
        "Version": "v1.0",
        "File Name": "sample.tif",
        "File Size": {"Value": 2048576, "Unit": "bytes"},
        "Image Width": {"Value": 1000, "Unit": "pixels"},
        "Image Height": {"Value": 1000, "Unit": "pixels"},
        "Bit Depth": {"Value": 8, "Unit": "bits"},
        "Pixel Width": {"Value": 264583.33, "Unit": "nm"},
        "Color Mode": "rgb",
        "Software": "SemiShopSoftware",
        "Time Stamp": "2023-10-15T14:30:25",
    },
    "Method Specific": {},
    "Tool Specific": {"Tool Name": "SemiShop v2.1", "Wafer ID": "Wafer_ID_12345"},
    "Customer Specific": {},
    "Data Evaluation": {},
    "History": [],
}


def create_temp_connector_file(connector_data=None):
    """Create a temporary connector file for testing"""
    if connector_data is None:
        connector_data = SAMPLE_CONNECTOR

    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(connector_data, temp_file, indent=2)
    temp_file.close()
    return temp_file.name


def create_mock_tiff_file(metadata=None):
    """Create a mock TIFF file for testing"""
    if metadata is None:
        metadata = SAMPLE_TIFF_METADATA

    temp_file = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    temp_file.close()
    return temp_file.name, metadata


def cleanup_temp_file(file_path):
    """Clean up temporary test files"""
    try:
        os.unlink(file_path)
    except (OSError, FileNotFoundError):
        pass
