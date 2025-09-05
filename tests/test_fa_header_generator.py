#!/usr/bin/env python3
"""
Test suite for FA Header Generator

This module contains comprehensive tests for the FA 4.0 header generation functionality.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import sys
import os

# Add the tools directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from fa_header_generator import FAHeaderGenerator, MetadataExtractor


class TestMetadataExtractor(unittest.TestCase):
    """Test cases for MetadataExtractor class"""

    def setUp(self):
        """Set up test fixtures"""
        self.extractor = MetadataExtractor()

    def test_extract_file_metadata_nonexistent_file(self):
        """Test that FileNotFoundError is raised for non-existent files"""
        with self.assertRaises(FileNotFoundError):
            self.extractor.extract_file_metadata("/nonexistent/file.tif")

    @patch("fa_header_generator.Path")
    def test_extract_file_metadata_basic_structure(self, mock_path):
        """Test basic metadata structure for existing file"""
        # Mock file path and stats
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_file.name = "test.tif"
        mock_file.stat.return_value = Mock(st_size=1024, st_mtime=1234567890)
        mock_path.return_value = mock_file

        # Mock the extraction methods to return empty dicts
        with (
            patch.object(self.extractor, "_extract_with_pillow", return_value={}),
            patch.object(self.extractor, "_extract_with_tifffile", return_value={}),
            patch.object(self.extractor, "_extract_with_exifread", return_value={}),
        ):
            result = self.extractor.extract_file_metadata("test.tif")

            # Check basic structure
            self.assertIn("file_path", result)
            self.assertIn("file_name", result)
            self.assertIn("file_size", result)
            self.assertIn("modified_time", result)
            self.assertIn("extraction_timestamp", result)
            self.assertIn("pillow", result)
            self.assertIn("tifffile", result)
            self.assertIn("exifread", result)


class TestFAHeaderGenerator(unittest.TestCase):
    """Test cases for FAHeaderGenerator class"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a sample connector configuration
        self.sample_connector = {
            "mappings": {
                "general_section": {
                    "File Name": {
                        "source": ["filename"],
                        "extraction": "file_metadata",
                        "required": True,
                    },
                    "Image Width": {
                        "source": ["pillow.width", "pillow.tags_v2.ImageWidth"],
                        "extraction": "first_available_numeric",
                        "unit": "pixels",
                        "required": True,
                    },
                }
            },
            "validation": {
                "required_fields": [
                    "general_section.File Name",
                    "general_section.Image Width",
                ],
                "optional_fields": [],
            },
        }

        # Create temporary connector file
        self.temp_connector = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(self.sample_connector, self.temp_connector)
        self.temp_connector.close()

        self.generator = FAHeaderGenerator(self.temp_connector.name)

    def tearDown(self):
        """Clean up test fixtures"""
        os.unlink(self.temp_connector.name)

    def test_load_connector(self):
        """Test connector loading functionality"""
        connector = self.generator.load_connector(self.temp_connector.name)
        self.assertEqual(connector, self.sample_connector)

    def test_clean_string_with_control_characters(self):
        """Test string cleaning functionality"""
        # Test with null bytes and control characters
        dirty_string = "Test\x00String\x01With\x1fControl\x7fChars\x9f"
        cleaned = self.generator._clean_string(dirty_string)
        self.assertEqual(cleaned, "TestStringWithControlChars")

    def test_clean_string_with_tuple(self):
        """Test string cleaning with tuple input"""
        tuple_input = ("Clean String\x00\x01", "second")
        cleaned = self.generator._clean_string(tuple_input)
        self.assertEqual(cleaned, "Clean String")

    def test_clean_string_with_none(self):
        """Test string cleaning with None input"""
        cleaned = self.generator._clean_string(None)
        self.assertEqual(cleaned, "")

    def test_parse_first_number_integer(self):
        """Test numeric parsing with integer"""
        result = self.generator._parse_first_number(42)
        self.assertEqual(result, 42)

    def test_parse_first_number_float(self):
        """Test numeric parsing with float"""
        result = self.generator._parse_first_number(3.14)
        self.assertEqual(result, 3.14)

    def test_parse_first_number_tuple(self):
        """Test numeric parsing with tuple"""
        result = self.generator._parse_first_number((123, 456))
        self.assertEqual(result, 123)

    def test_parse_first_number_string(self):
        """Test numeric parsing with string containing numbers"""
        result = self.generator._parse_first_number("Image size: 1024x768")
        self.assertEqual(result, 1024)

    def test_parse_first_number_float_string(self):
        """Test numeric parsing with string containing float"""
        result = self.generator._parse_first_number("Resolution: 96.5 DPI")
        self.assertEqual(result, 96.5)

    def test_parse_first_number_no_numbers(self):
        """Test numeric parsing with string containing no numbers"""
        result = self.generator._parse_first_number("No numbers here")
        self.assertIsNone(result)

    def test_get_first_valid_string_tuple(self):
        """Test string extraction from tuple"""
        result = self.generator._get_first_valid_string(("first", "second"))
        self.assertEqual(result, "first")

    def test_get_first_valid_string_list(self):
        """Test string extraction from list"""
        result = self.generator._get_first_valid_string(["first", "second"])
        self.assertEqual(result, "first")

    def test_get_first_valid_string_direct(self):
        """Test string extraction from direct string"""
        result = self.generator._get_first_valid_string("direct string")
        self.assertEqual(result, "direct string")

    def test_datetime_to_iso8601_tiff_format(self):
        """Test datetime conversion from TIFF format"""
        result = self.generator._datetime_to_iso8601("2023:10:15 14:30:25")
        self.assertEqual(result, "2023-10-15T14:30:25")

    def test_datetime_to_iso8601_standard_format(self):
        """Test datetime conversion from standard format"""
        result = self.generator._datetime_to_iso8601("2023-10-15 14:30:25")
        self.assertEqual(result, "2023-10-15T14:30:25")

    def test_datetime_to_iso8601_invalid_format(self):
        """Test datetime conversion with invalid format"""
        result = self.generator._datetime_to_iso8601("invalid date")
        self.assertEqual(result, "invalid date")

    def test_datetime_to_iso8601_empty(self):
        """Test datetime conversion with empty input"""
        result = self.generator._datetime_to_iso8601("")
        self.assertIsNone(result)

    def test_resolution_to_pixel_size(self):
        """Test DPI to nanometer conversion"""
        # 96 DPI should convert to approximately 264583.33 nm/pixel
        result = self.generator._resolution_to_pixel_size(96)
        expected = 25400000 / 96  # 264583.33...
        self.assertAlmostEqual(result, round(expected, 2))

    def test_resolution_to_pixel_size_zero(self):
        """Test DPI conversion with zero value"""
        result = self.generator._resolution_to_pixel_size(0)
        self.assertIsNone(result)

    def test_resolution_to_pixel_size_none(self):
        """Test DPI conversion with None value"""
        result = self.generator._resolution_to_pixel_size(None)
        self.assertIsNone(result)

    def test_normalize_color_mode_grayscale(self):
        """Test color mode normalization for grayscale"""
        test_cases = ["L", "grayscale", "grey", "gray", "GRAYSCALE"]
        for case in test_cases:
            result = self.generator._normalize_color_mode(case)
            self.assertEqual(result, "grayscale")

    def test_normalize_color_mode_rgb(self):
        """Test color mode normalization for RGB"""
        test_cases = ["RGB", "rgb", "RGBA", "rgba"]
        for case in test_cases:
            result = self.generator._normalize_color_mode(case)
            self.assertEqual(result, "rgb")

    def test_normalize_color_mode_palette(self):
        """Test color mode normalization for palette"""
        test_cases = ["P", "palette", "PALETTE"]
        for case in test_cases:
            result = self.generator._normalize_color_mode(case)
            self.assertEqual(result, "palette")

    def test_extract_value_from_source_simple(self):
        """Test value extraction with simple path"""
        metadata = {"pillow": {"width": 1024}}
        result = self.generator.extract_value_from_source(metadata, "pillow.width")
        self.assertEqual(result, 1024)

    def test_extract_value_from_source_nested(self):
        """Test value extraction with nested path"""
        metadata = {"pillow": {"basic_info": {"format": "TIFF"}}}
        result = self.generator.extract_value_from_source(
            metadata, "pillow.basic_info.format"
        )
        self.assertEqual(result, "TIFF")

    def test_extract_value_from_source_missing(self):
        """Test value extraction with missing path"""
        metadata = {"pillow": {"width": 1024}}
        result = self.generator.extract_value_from_source(metadata, "pillow.height")
        self.assertIsNone(result)

    def test_resolve_field_value_filename(self):
        """Test field resolution for filename"""
        metadata = {"file_path": "/path/to/test.tif"}
        field_config = {"source": ["filename"]}
        result = self.generator.resolve_field_value(metadata, field_config)
        self.assertEqual(result, "test.tif")

    def test_resolve_field_value_file_size(self):
        """Test field resolution for file size"""
        metadata = {"file_size": 1024}
        field_config = {"source": ["file_size"]}
        result = self.generator.resolve_field_value(metadata, field_config)
        self.assertEqual(result, 1024)

    def test_resolve_field_value_with_transformation(self):
        """Test field resolution with transformation"""
        metadata = {"pillow": {"tags_v2": {"Software": "Test\x00Software\x01"}}}
        field_config = {
            "source": ["pillow.tags_v2.Software"],
            "transformation": "clean_string",
        }
        result = self.generator.resolve_field_value(metadata, field_config)
        self.assertEqual(result, "TestSoftware")

    def test_resolve_field_value_multiple_sources(self):
        """Test field resolution with multiple sources (fallback)"""
        metadata = {"pillow": {"width": 1024}}
        field_config = {"source": ["missing.source", "pillow.width", "another.missing"]}
        result = self.generator.resolve_field_value(metadata, field_config)
        self.assertEqual(result, 1024)

    def test_apply_transformation_clean_string(self):
        """Test transformation application for string cleaning"""
        result = self.generator.apply_transformation("Dirty\x00String", "clean_string")
        self.assertEqual(result, "DirtyString")

    def test_apply_transformation_unknown(self):
        """Test transformation application for unknown transformation"""
        result = self.generator.apply_transformation("test", "unknown_transformation")
        self.assertEqual(result, "test")

    @patch.object(FAHeaderGenerator, "extract_tiff_metadata")
    def test_generate_fa40_header_basic_structure(self, mock_extract):
        """Test FA 4.0 header generation basic structure"""
        # Mock metadata
        mock_extract.return_value = {
            "file_path": "/test/sample.tif",
            "file_size": 1024,
            "pillow": {"width": 800},
        }

        result = self.generator.generate_fa_header("/test/sample.tif")

        # Check basic structure
        self.assertIn("General Section", result)
        self.assertIn("Method Specific", result)
        self.assertIn("Tool Specific", result)
        self.assertIn("Customer Specific", result)
        self.assertIn("Data Evaluation", result)
        self.assertIn("History", result)

        # Check generated metadata
        self.assertEqual(
            result["General Section"]["Header Type"], "FA standardized header"
        )
        self.assertEqual(result["General Section"]["Version"], "v1.0")
        self.assertIn("Time Stamp", result["General Section"])
        self.assertIn("File Path", result["General Section"])

    @patch.object(FAHeaderGenerator, "extract_tiff_metadata")
    def test_generate_fa40_header_with_mappings(self, mock_extract):
        """Test FA 4.0 header generation with field mappings"""
        # Mock metadata
        mock_extract.return_value = {
            "file_path": "/test/sample.tif",
            "file_size": 1024,
            "pillow": {"width": 800},
        }

        result = self.generator.generate_fa_header("/test/sample.tif")

        # Check mapped fields
        self.assertEqual(result["General Section"]["File Name"], "sample.tif")
        self.assertEqual(result["General Section"]["Image Width"]["Value"], 800)
        self.assertEqual(result["General Section"]["Image Width"]["Unit"], "pixels")

    def test_validate_header_all_required_present(self):
        """Test header validation with all required fields present"""
        header = {
            "General Section": {
                "File Name": "test.tif",
                "Image Width": {"Value": 800, "Unit": "pixels"},
            }
        }

        validation = self.generator.validate_header(header)

        self.assertEqual(validation["missing_required"], [])
        self.assertEqual(len(validation["present_optional"]), 0)

    def test_validate_header_missing_required(self):
        """Test header validation with missing required fields"""
        header = {
            "General Section": {
                "File Name": "test.tif"
                # Missing Image Width
            }
        }

        validation = self.generator.validate_header(header)

        self.assertIn("general_section.Image Width", validation["missing_required"])

    @patch("builtins.open", new_callable=mock_open)
    @patch.object(FAHeaderGenerator, "extract_tiff_metadata")
    def test_generate_fa40_header_save_to_file(self, mock_extract, mock_file):
        """Test FA 4.0 header generation with file output"""
        # Mock metadata
        mock_extract.return_value = {
            "file_path": "/test/sample.tif",
            "file_size": 1024,
            "pillow": {"width": 800},
        }

        self.generator.generate_fa_header("/test/sample.tif", "output.json")

        # Verify file was opened for writing
        mock_file.assert_called_once_with("output.json", "w", encoding="utf-8")


class TestTransformationFunctions(unittest.TestCase):
    """Test cases for specific transformation functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.generator = FAHeaderGenerator.__new__(FAHeaderGenerator)

    def test_clean_string_edge_cases(self):
        """Test string cleaning with various edge cases"""
        test_cases = [
            ("", ""),
            ("   ", ""),
            ("normal string", "normal string"),
            ("\x00\x01\x02test\x03\x04", "test"),
            (("tuple_string\x00",), "tuple_string"),
            (123, "123"),
            (None, ""),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = self.generator._clean_string(input_val)
                self.assertEqual(result, expected)

    def test_parse_first_number_edge_cases(self):
        """Test number parsing with various edge cases"""
        test_cases = [
            ("", None),
            ("no numbers", None),
            ("-123.45", -123.45),
            ("3.14159", 3.14159),
            ("Image: 1920x1080", 1920),
            ([456.78], 456.78),
            ((789,), 789),
            ("0", 0),
            ("0.0", 0.0),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = self.generator._parse_first_number(input_val)
                self.assertEqual(result, expected)

    def test_resolution_calculations(self):
        """Test DPI to nanometer conversion calculations"""
        test_cases = [
            (72, 352777.78),  # 72 DPI (common screen resolution)
            (96, 264583.33),  # 96 DPI (common screen resolution)
            (300, 84666.67),  # 300 DPI (print resolution)
            (600, 42333.33),  # 600 DPI (high print resolution)
        ]

        for dpi, expected_nm in test_cases:
            with self.subTest(dpi=dpi):
                result = self.generator._resolution_to_pixel_size(dpi)
                self.assertAlmostEqual(result, expected_nm, places=2)


if __name__ == "__main__":
    # Create a test suite
    unittest.main(verbosity=2)
