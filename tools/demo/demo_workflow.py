#!/usr/bin/env python3
"""
TIFF to FA 4.0 Demo Script

This script demonstrates the complete workflow from TIFF metadata extraction
to FA 4.0 header generation using connector mappings.
"""

from pathlib import Path
from tools.fa_header_generator import FA40HeaderGenerator


def demo_workflow():
    """Demonstrate the complete TIFF to FA 4.0 workflow"""

    print("=" * 70)
    print("TIFF TO FA 4.0 HEADER GENERATION DEMO")
    print("=" * 70)

    # Define paths
    tiff_file = "scratch/lem/003_Ref_20x_WatchdogRunning.tif"
    connector_file = "connectors/general_image_connector.json"
    output_file = "demo_fa40_header.json"

    # Check if files exist
    if not Path(tiff_file).exists():
        print(f"❌ TIFF file not found: {tiff_file}")
        return

    if not Path(connector_file).exists():
        print(f"❌ Connector file not found: {connector_file}")
        return

    print(f"📁 Input TIFF: {tiff_file}")
    print(f"🔗 Connector: {connector_file}")
    print(f"💾 Output: {output_file}")
    print()

    try:
        # Initialize generator
        print("🔧 Initializing FA 4.0 Header Generator...")
        generator = FA40HeaderGenerator(connector_file)

        # Generate header
        print("🔍 Extracting metadata and generating FA 4.0 header...")
        header = generator.generate_fa40_header(tiff_file, output_file)

        # Validate
        print("✅ Validating generated header...")
        validation = generator.validate_header(header)

        # Print summary
        print("\n" + "=" * 50)
        print("GENERATION SUMMARY")
        print("=" * 50)

        general_section = header.get("General Section", {})
        print(
            f"📏 Image Dimensions: {general_section.get('Image Width', {}).get('Value', 'N/A')} x {general_section.get('Image Height', {}).get('Value', 'N/A')} pixels"
        )
        print(f"🎨 Color Mode: {general_section.get('Color Mode', 'N/A')}")
        print(f"🔢 Bit Depth: {general_section.get('Bit Depth', 'N/A')}")
        print(
            f"📦 File Size: {general_section.get('File Size', {}).get('Value', 'N/A')} bytes"
        )
        print(f"🏭 Manufacturer: {general_section.get('Manufacturer', 'N/A')}")
        print(f"🔧 Tool: {general_section.get('Tool Name', 'N/A')}")
        print(f"💻 Software: {general_section.get('Software', 'N/A')}")

        # Validation summary
        missing_required = len(validation.get("missing_required", []))
        present_optional = len(validation.get("present_optional", []))

        print(f"\n✅ Required fields: {6 - missing_required}/6 present")
        print(f"✨ Optional fields: {present_optional} present")

        if missing_required == 0:
            print("🎉 All required fields successfully mapped!")
        else:
            print(f"⚠️  {missing_required} required fields missing")

        print(f"\n💾 FA 4.0 header saved to: {output_file}")

        # Show key insights
        print("\n" + "=" * 50)
        print("KEY INSIGHTS")
        print("=" * 50)

        pixel_width = general_section.get("Pixel Width", {}).get("Value")
        pixel_height = general_section.get("Pixel Height", {}).get("Value")

        if pixel_width and pixel_height:
            print(f"🔬 Pixel size: {pixel_width:.1f} x {pixel_height:.1f} nm")
            print(
                f"📐 Field of view: {pixel_width * general_section.get('Image Width', {}).get('Value', 0) / 1000:.1f} x {pixel_height * general_section.get('Image Height', {}).get('Value', 0) / 1000:.1f} μm"
            )

        # Check for SemiShop signature
        software = general_section.get("Software", "")
        if "SemiShop" in software:
            print("🔍 Detected: SemiShop microscopy software")
            print(
                "💡 Recommendation: Use SemiShop-specific connector for better metadata extraction"
            )

        print("\n" + "=" * 50)
        print("NEXT STEPS")
        print("=" * 50)
        print("1. 🔧 Clean up binary artifacts in text fields")
        print("2. 📋 Create tool-specific connector for better metadata mapping")
        print("3. 🔍 Analyze custom tags (32000-32999) for method-specific data")
        print("4. ✅ Validate with additional TIFF files from the same tool")

    except Exception as e:
        print(f"❌ Error during header generation: {e}")
        import traceback

        traceback.print_exc()


def compare_headers():
    """Compare headers generated from different TIFF files"""

    print("\n" + "=" * 70)
    print("COMPARING MULTIPLE TIFF FILES")
    print("=" * 70)

    tiff_files = [
        "scratch/lem/003_Ref_20x_WatchdogRunning.tif",
        "scratch/lem/Fail_1 Loop_20X_Overlay_11.tiff",
    ]

    connector_file = "connectors/general_image_connector.json"

    if not Path(connector_file).exists():
        print(f"❌ Connector file not found: {connector_file}")
        return

    generator = FA40HeaderGenerator(connector_file)
    headers = {}

    for tiff_file in tiff_files:
        if Path(tiff_file).exists():
            print(f"📁 Processing: {Path(tiff_file).name}")
            try:
                header = generator.generate_fa40_header(tiff_file)
                headers[Path(tiff_file).name] = header
            except Exception as e:
                print(f"❌ Error processing {tiff_file}: {e}")

    # Compare key properties
    print("\n📊 COMPARISON TABLE")
    print("-" * 70)
    print(f"{'Property':<20} {'File 1':<25} {'File 2':<25}")
    print("-" * 70)

    if len(headers) >= 2:
        files = list(headers.keys())

        properties = [
            ("Image Width", "Image Width"),
            ("Image Height", "Image Height"),
            ("Bit Depth", "Bit Depth"),
            ("Color Mode", "Color Mode"),
            ("File Size", "File Size"),
            ("Software", "Software"),
        ]

        for prop_name, prop_key in properties:
            values = []
            for file_name in files[:2]:
                gs = headers[file_name].get("General Section", {})
                value = gs.get(prop_key, "N/A")
                if isinstance(value, dict) and "Value" in value:
                    value = f"{value['Value']} {value.get('Unit', '')}"
                values.append(str(value)[:24])

            print(f"{prop_name:<20} {values[0]:<25} {values[1]:<25}")


if __name__ == "__main__":
    demo_workflow()
    compare_headers()
