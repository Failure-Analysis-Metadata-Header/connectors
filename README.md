# connectors
This repository contains FA Header connector files, which are essentially dictionaries mapping metadata from some source format to the FA Header format.

The idea is to create these connector files for data from different manufacturers in order to simplify the creation of metadata in the standardized FA Header format.

# FA 4.0 Header Generation System - Implementation Summary

## Overview

I've successfully created a complete system for extracting metadata from TIFF files and generating standardized FA 4.0 JSON headers using configurable connector mappings.

## Components Created

### 1. Updated Connector Format
**File**: `connectors/general_image_connector.json`

The connector file now uses a comprehensive format with:
- **Tool identification**: Signature patterns and applicability
- **Mappings**: Source-to-target field mappings with multiple fallback sources
- **Transformations**: Data cleaning and conversion specifications
- **Validation**: Required and optional field definitions

### 2. FA 4.0 Header Generator
**File**: `fa40_header_generator.py`

**Key Features:**
- Self-contained TIFF metadata extraction (Pillow, tifffile, exifread)
- Configurable field mapping using connector files
- Automatic data type conversions and cleaning
- FA 4.0 compliant JSON structure generation
- Built-in validation against connector requirements

**Core Functions:**
```python
# Initialize with connector
generator = FA40HeaderGenerator("connector.json")

# Generate FA 4.0 header
header = generator.generate_fa40_header("image.tif", "output.json")

# Validate results
validation = generator.validate_header(header)
```

### 3. Demonstration Workflow
**File**: `demo_fa40_workflow.py`

Complete demonstration showing:
- Single file processing
- Multi-file comparison
- Validation reporting
- Key insights extraction

## Test Results

Successfully tested with your TIFF files:

### File 1: `003_Ref_20x_WatchdogRunning.tif`
- **Dimensions**: 1000×1000 pixels, 8-bit
- **Pixel size**: 866×874 nm
- **Field of view**: 866×874 μm  
- **Software**: SemiShop (with binary artifacts)
- **All required fields**: ✅ Successfully mapped

### File 2: `Fail_1 Loop_20X_Overlay_11.tiff`
- **Dimensions**: 640×640 pixels, 8-bit
- **Color mode**: RGB vs. Palette (different from file 1)
- **Software detection**: Limited metadata available

## Generated FA 4.0 Structure

```json
{
  "General Section": {
    "File Name": "003_Ref_20x_WatchdogRunning.tif",
    "File Size": {"Value": 1003582, "Unit": "bytes"},
    "File Format": "TIFF", 
    "Image Width": {"Value": 1000, "Unit": "pixels"},
    "Image Height": {"Value": 1000, "Unit": "pixels"},
    "Bit Depth": 8,
    "Pixel Width": {"Value": 866.0, "Unit": "nm"},
    "Pixel Height": {"Value": 874.0, "Unit": "nm"},
    "Color Mode": "palette",
    "Manufacturer": "HPK_SYSTEME",
    "Tool Name": "SemiShop", 
    "Software": "SemiShop",
    "Time Stamp": "2025-09-04T11:20:04.523650",
    "Header Type": "FA4.0 standardized header",
    "Version": "v1.0"
  },
  "Method Specific": {},
  "Tool Specific": {},
  "Customer Specific": {},
  "Data Evaluation": {},
  "History": {}
}
```

## Key Features Implemented

### ✅ Robust Metadata Extraction
- Multiple library support with fallbacks
- Handles binary data and encoding issues
- Extracts standard and custom TIFF tags

### ✅ Flexible Mapping System
- Multiple source priorities per field
- Configurable transformations
- Unit conversions (DPI → nanometers)
- String cleaning and normalization

### ✅ FA 4.0 Compliance
- Proper JSON structure matching schema
- Value/Unit object format for measurements
- Required field validation
- Extensible section support

### ✅ Data Transformations
- **String cleaning**: Removes binary artifacts
- **Resolution conversion**: DPI to nanometers
- **Timestamp normalization**: ISO8601 format
- **Color mode mapping**: Standardized terms
- **Numeric extraction**: From various formats

## Usage Examples

### Basic Usage
```bash
# Generate FA 4.0 header from TIFF
python fa40_header_generator.py image.tif connector.json

# With validation and preview
python fa40_header_generator.py image.tif connector.json --validate --pretty-print

# Custom output location
python fa40_header_generator.py image.tif connector.json -o custom_header.json
```

### Programmatic Usage
```python
from fa40_header_generator import FA40HeaderGenerator

# Initialize
generator = FA40HeaderGenerator("connector.json")

# Process file
header = generator.generate_fa40_header("image.tif")

# Validate
validation = generator.validate_header(header)
print(f"Missing required: {validation['missing_required']}")
```

## Current Status & Recommendations

### ✅ Working Successfully
- Basic image metadata extraction and mapping
- FA 4.0 compliant JSON generation
- Multi-source metadata handling
- Validation and error reporting

### 🔧 Areas for Improvement

1. **Binary Data Cleanup**: Some text fields contain binary artifacts
2. **Custom Tag Mapping**: SemiShop custom tags (32000-32999) need tool-specific connectors
3. **Method-Specific Data**: Microscopy parameters not yet extracted
4. **Timestamp Parsing**: Need better datetime format detection

### 📋 Next Steps

1. **Create SemiShop-specific connector** for custom tags analysis
2. **Improve string cleaning** algorithms for binary artifacts
3. **Add method-specific mappings** for microscopy metadata
4. **Test with more TIFF files** from different instruments
5. **Document custom tag meanings** with manufacturer specs

## Files Structure

```
connectors/
├── connectors/
│   └── general_image_connector.json     # Updated connector format
├── fa40_header_generator.py             # Main generator tool
├── demo_fa40_workflow.py                # Demonstration script
├── tiff_metadata_extractor.py           # Metadata extraction
├── metadata_inspector.py                # Interactive inspection
└── schema/                              # FA 4.0 schema files
    ├── General Section.json
    ├── Method Specific.json
    └── ... (other schema files)
```

The system is ready for production use with basic TIFF files and can be extended with tool-specific connectors for specialized metadata extraction.


## Tools Overview

### 1. `tiff_metadata_extractor.py`
**Primary tool for extracting all metadata from TIFF files**

**Features:**
- Extracts metadata using multiple libraries (Pillow, tifffile, exifread)
- Comprehensive tag discovery across all sources
- Handles custom/proprietary tags (32000-32999 range)
- Supports single files or directory scanning
- Outputs detailed JSON reports

**Usage:**
```bash
# Extract metadata from a single file
python tiff_metadata_extractor.py path/to/file.tif

# Extract from all TIFF files in directory (recursive)
python tiff_metadata_extractor.py path/to/directory --recursive

# Save results to custom location
python tiff_metadata_extractor.py path/to/directory -o my_results.json

# Only show tag summary (don't save full data)
python tiff_metadata_extractor.py path/to/directory --tags-only
```

### 2. `fa40_mapper.py`
**Analyzes extracted metadata and suggests mappings to FA 4.0 header format**

**Features:**
- Analyzes metadata against FA 4.0 JSON schema
- Provides confidence scores for mapping suggestions
- Identifies high-priority mappings
- Generates comprehensive mapping reports

**Usage:**
```bash
# Analyze extracted metadata
python fa40_mapper.py tiff_metadata_extraction_results.json

# Save mapping analysis to file
python fa40_mapper.py tiff_metadata_extraction_results.json -o mapping_report.json

# Use custom schema directory
python fa40_mapper.py results.json -s /path/to/schema/dir
```

### 3. `metadata_inspector.py`
**Interactive tool for inspecting specific metadata values**

**Features:**
- List all files in metadata
- Inspect specific tags across sources
- View custom/proprietary tags
- Compare tags across multiple files

**Usage:**
```bash
# List all files in metadata
python metadata_inspector.py results.json list

# Inspect specific tag (e.g., software info)
python metadata_inspector.py results.json inspect "software"

# View all custom tags (32000-32999)
python metadata_inspector.py results.json custom

# Compare a tag across all files
python metadata_inspector.py results.json compare "ImageWidth"

# Inspect specific file (by index)
python metadata_inspector.py results.json inspect "magnification" -f 1
```

## Quick Start Guide

### Step 1: Extract Metadata
```bash
# Extract metadata from your TIFF files
python tiff_metadata_extractor.py scratch/lem --recursive -o my_tiff_metadata.json
```

### Step 2: Analyze Mappings
```bash
# Get mapping suggestions for FA 4.0 header
python fa40_mapper.py my_tiff_metadata.json -o mapping_analysis.json
```

### Step 3: Inspect Specific Values
```bash
# Look at custom tags (manufacturer-specific data)
python metadata_inspector.py my_tiff_metadata.json custom

# Inspect specific measurements
python metadata_inspector.py my_tiff_metadata.json inspect "current"
python metadata_inspector.py my_tiff_metadata.json inspect "voltage"
```

## Understanding the Output

### Metadata Extraction Results
The extraction tool creates a JSON file with:
- **extraction_summary**: Overall statistics and library status
- **tag_summary**: All unique tags found, organized by source
- **full_metadata**: Complete metadata for each file

### Mapping Analysis
The mapping tool provides:
- **mapping_candidates**: Suggested mappings with confidence scores
- **recommendations**: Actionable next steps
- **schema_coverage**: Which FA 4.0 fields can be populated

### Key Metadata Sources

1. **Standard TIFF Tags**: Basic image properties (width, height, resolution, etc.)
2. **EXIF Data**: Camera/device information, timestamps
3. **Custom Tags (32000-32999)**: Manufacturer-specific metadata
   - Often contains the most valuable information for FA 4.0 mapping
   - Requires manufacturer documentation to decode

## Creating Connector Files

Based on the analysis, create connector files that map specific TIFF metadata to FA 4.0 format:

1. **Identify tool signature**: Software name, manufacturer, or custom tag patterns
2. **Map standard fields**: Image dimensions, timestamps, basic properties
3. **Decode custom tags**: Use manufacturer documentation or reverse engineering
4. **Define transformations**: Unit conversions, string cleaning, format changes

See `semishop_tiff_connector.json` for an example connector file structure.

## FA 4.0 Schema Structure

The FA 4.0 header consists of these main sections:
- **General Section**: Universal fields (dimensions, timestamps, tool info)
- **Method Specific**: Technique-specific metadata (SEM, FIB, Optical Microscopy)
- **Tool Specific**: Manufacturer/model-specific data
- **Customer Section**: Customer-defined fields
- **Data Evaluation**: Analysis results, ROIs, measurements
- **History**: Workflow tracking

## Tips for Effective Mapping

### High-Confidence Mappings (Start Here)
- Image dimensions (Width, Height)
- Bit depth
- Software/tool identification
- File properties

### Medium-Confidence Mappings (Verify)
- Timestamps (check format)
- Resolution/pixel size (check units)
- Manufacturer/model info

### Low-Confidence Mappings (Research Required)
- Custom tags (32000+ range)
- Method-specific parameters
- Coordinate systems
- Measurement values

### Common Issues
1. **Binary Data in Text Fields**: Clean null bytes and control characters
2. **Unit Conversions**: DPI to nm, seconds to ms, etc.
3. **Format Variations**: Different timestamp formats, measurement notations
4. **Nested Data**: Complex structures in custom tags

## Dependencies

Install required packages:
```bash
pip install Pillow tifffile exifread
```

## Troubleshooting

### No metadata found
- Check file format (must be TIFF/TIF)
- Verify file integrity
- Some TIFF files may have minimal metadata

### Custom tags not readable
- Try different extraction libraries
- Check for proprietary software requirements
- Contact manufacturer for tag documentation

### Mapping confidence low
- Inspect raw values with metadata_inspector.py
- Check for alternative tag names
- Look for patterns in custom tag ranges

## Next Steps

1. **Run the tools** on your TIFF files
2. **Review high-confidence mappings** and implement them first
3. **Research custom tags** using manufacturer documentation
4. **Create connector files** for each tool/manufacturer
5. **Test and validate** the mappings with sample data
6. **Iterate and refine** based on results

The goal is to create a library of connector files that can automatically transform TIFF metadata into standardized FA 4.0 headers for your specific tools and workflows.
