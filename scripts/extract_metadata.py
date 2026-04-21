#!/usr/bin/env python3
import os
import re
import json
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MetadataExtractor:
    def __init__(self, codebase_path):
        self.codebase_path = codebase_path
        self.metadata = {}

    def extract_from_file(self, rel_path, pattern, group_index=1):
        """Extracts metadata using regex from a file."""
        abs_path = os.path.join(self.codebase_path, rel_path)
        if not os.path.exists(abs_path):
            logging.warning(f"Source file not found: {rel_path}")
            return None
        
        try:
            with open(abs_path, 'r') as f:
                content = f.read()
                match = re.search(pattern, content)
                if match:
                    value = match.group(group_index).strip()
                    logging.info(f"Extracted from {rel_path}: {value}")
                    return value
        except Exception as e:
            logging.error(f"Error reading {rel_path}: {e}")
        
        return None

    def extract_from_prop(self, rel_path, prop_key):
        """Extracts metadata from a .prop file."""
        abs_path = os.path.join(self.codebase_path, rel_path)
        if not os.path.exists(abs_path):
            return None
        
        try:
            with open(abs_path, 'r') as f:
                for line in f:
                    if line.startswith(f"{prop_key}="):
                        value = line.split('=', 1)[1].strip()
                        logging.info(f"Extracted from {rel_path} ({prop_key}): {value}")
                        return value
        except Exception as e:
            logging.error(f"Error reading {rel_path}: {e}")
        
        return None

    def run_discovery(self):
        """Discovers all defined metadata from codebase."""
        # 1. Security Patch
        self.metadata['security_patch'] = self.extract_from_file(
            'build/make/core/version_defaults.mk', 
            r'PLATFORM_SECURITY_PATCH\s*:=\s*([\d-]+)'
        )

        # 2. Android Version
        self.metadata['android_version'] = self.extract_from_file(
            'build/make/core/version_defaults.mk', 
            r'PLATFORM_VERSION\s*:=\s*(\d+)'
        )

        # 3. Build Info (from generated build.prop if available)
        # Note: This requires the build to have finished at least once
        build_prop_path = 'out/target/product/thorpe/build.prop'
        self.metadata['build_display_id'] = self.extract_from_prop(build_prop_path, 'ro.build.display.id')
        self.metadata['fingerprint'] = self.extract_from_prop(build_prop_path, 'ro.build.fingerprint')

        # 4. GMS Version (Example pattern)
        self.metadata['gms_version'] = self.extract_from_file(
            'vendor/google/products/gms.mk',
            r'PRODUCT_GMS_VERSION\s*:=\s*([\w_]+)'
        )

        # 5. Kernel Version (Example from generated header)
        self.metadata['kernel_version'] = self.extract_from_file(
            'out/target/product/thorpe/obj/KERNEL_OBJ/include/generated/utsrelease.h',
            r'#define UTS_RELEASE\s*"([^"]+)"'
        )

        return self.metadata

    def process_template(self, template_path, output_path):
        """Reads template, injects metadata, and filters missing items."""
        if not os.path.exists(template_path):
            logging.error(f"Template not found: {template_path}")
            return False
        
        with open(template_path, 'r') as f:
            data = json.load(f)

        # Update basic release info
        if "release" in data:
            if self.metadata.get('build_display_id'):
                data["release"]["build_id"] = self.metadata['build_display_id']
                # Extract clean version if possible
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', self.metadata['build_display_id'])
                if match:
                    data["release"]["version"] = match.group(1)
            
            if self.metadata.get('security_patch'):
                data["release"]["date"] = self.metadata['security_patch']

        # Process validations
        new_validations = []
        for item in data.get("validations", []):
            expected = item.get("expected", "")
            
            # Placeholder mapping
            placeholders = {
                "__SECURITY_PATCH__": "security_patch",
                "__ANDROID_VERSION__": "android_version",
                "__BUILD_ID__": "build_display_id",
                "__FINGERPRINT__": "fingerprint",
                "__GMS_VERSION__": "gms_version",
                "__KERNEL_VERSION__": "kernel_version"
            }

            if expected in placeholders:
                key = placeholders[expected]
                val = self.metadata.get(key)
                if val:
                    item["expected"] = val
                    new_validations.append(item)
                else:
                    logging.warning(f"Field '{item['name']}' ({expected}) could not be discovered. Dropping validation.")
            else:
                # Keep items without placeholders
                new_validations.append(item)
        
        data["validations"] = new_validations

        # Write output
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        logging.info(f"Generated build_info.json at {output_path}")
        return True

def main():
    parser = argparse.ArgumentParser(description="Extract metadata from Android codebase.")
    parser.add_argument("--codebase", required=True, help="Path to Android codebase root")
    parser.add_argument("--template", required=True, help="Path to build_info.json template")
    parser.add_argument("--output", default="build_info.json", help="Path to output file")
    
    args = parser.parse_args()
    
    extractor = MetadataExtractor(args.codebase)
    extractor.run_discovery()
    extractor.process_template(args.template, args.output)

if __name__ == "__main__":
    main()
