#!/usr/bin/env python3
"""
Standalone CSV Bulk Import Script for STL Collection
Imports entries via HTTP API to remote or local server

Usage:
    python bulk_import_standalone.py import.csv --url http://localhost:8000 --username admin --password pass --test
    python bulk_import_standalone.py import.csv --url http://localhost:8000 --username admin --password pass
    python bulk_import_standalone.py import.csv --url https://your-server.com --username admin --password pass --verbose
"""

import csv
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

try:
    import requests
    from requests.auth import HTTPBasicAuth
except ImportError:
    print("Error: 'requests' library not installed")
    print("Install with: pip install requests")
    sys.exit(1)


class STLCollectionImporter:
    """HTTP API client for STL Collection bulk import"""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        
    def health_check(self) -> bool:
        """Test API connection and authentication"""
        try:
            response = self.session.get(f'{self.base_url}/upload/api/health/', timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Connected to {self.base_url}")
                print(f"✓ Authenticated as: {data.get('username')}")
                return True
            else:
                print(f"✗ Health check failed: {response.status_code}")
                if response.status_code == 401:
                    print("  Authentication failed - check username/password")
                return False
        except requests.exceptions.ConnectionError:
            print(f"✗ Connection error: Cannot reach {self.base_url}")
            return False
        except requests.exceptions.Timeout:
            print(f"✗ Connection timeout: Server took too long to respond")
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    def get_existing_tags(self) -> Dict[str, List[str]]:
        """Fetch all existing tags from server grouped by tag type"""
        try:
            response = self.session.get(
                f'{self.base_url}/upload/api/get-tags/',
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('tags', {})
            else:
                print(f"    Warning: Could not fetch tags - HTTP {response.status_code}")
                return {}
        except Exception as e:
            print(f"    Warning: Could not fetch tags - {e}")
            return {}
    
    def check_duplicate(self, name: str, publisher: str, range_name: str) -> Tuple[bool, int]:
        """Check if entry exists on server"""
        params = {
            'name': name,
            'publisher': publisher,
            'range': range_name
        }
        
        try:
            response = self.session.get(
                f'{self.base_url}/upload/api/check-duplicate/',
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('exists', False), data.get('entry_id')
            return False, None
        except Exception as e:
            print(f"    Warning: Could not check duplicate - {e}")
            return False, None
    
    def create_entry(self, row: Dict) -> Tuple[bool, int, str]:
        """Create entry with tags via API"""
        name = row.get('Name', '').strip()
        publisher = row.get('Publisher', '').strip()
        range_name = row.get('Range', '').strip()
        folder_path = row.get('Folder path', '').strip()
        
        # Parse tags from CSV
        tags = {}
        
        # Publisher tag
        if publisher:
            tags['Publisher'] = [publisher]
        
        # Faction Tag
        if row.get('Faction Tag', '').strip():
            tags['Faction Tag'] = [row['Faction Tag'].strip()]
        
        # Army Role
        if row.get('Army Role', '').strip():
            tags['Army Role'] = [row['Army Role'].strip()]
        
        # GW Alternative (semicolon-separated)
        gw_alt = row.get('GW Alternative', '').strip()
        if gw_alt:
            tags['GW Alternative'] = [x.strip() for x in gw_alt.split(';') if x.strip()]
        
        payload = {
            'name': name,
            'publisher': publisher,
            'range': range_name,
            'folder_location': folder_path,
            'tags': tags
        }
        
        try:
            response = self.session.post(
                f'{self.base_url}/upload/api/create-entry/',
                json=payload,
                timeout=30
            )
            
            if response.status_code == 201:
                data = response.json()
                return True, data.get('entry_id'), data.get('entry_name')
            elif response.status_code == 409:
                data = response.json()
                return False, data.get('entry_id'), f"Duplicate: {data.get('error')}"
            else:
                error_msg = response.json().get('error', response.text) if response.text else f"HTTP {response.status_code}"
                return False, None, f"Error: {error_msg}"
                
        except Exception as e:
            return False, None, f"Exception: {str(e)}"
    
    def upload_image(self, entry_id: int, image_path: Path, is_primary: bool) -> Tuple[bool, str]:
        """Upload single image file via API"""
        try:
            with open(image_path, 'rb') as f:
                files = {'image': (image_path.name, f)}
                data = {
                    'entry_id': str(entry_id),
                    'is_primary': 'true' if is_primary else 'false'
                }
                
                response = self.session.post(
                    f'{self.base_url}/upload/api/upload-image/',
                    files=files,
                    data=data,
                    timeout=60
                )
                
                if response.status_code == 201:
                    result = response.json()
                    return True, result.get('filename')
                else:
                    error_msg = response.json().get('error', response.text) if response.text else f"HTTP {response.status_code}"
                    return False, f"Error: {error_msg}"
                    
        except Exception as e:
            return False, str(e)
    
    def validate_row(self, row: Dict, row_num: int) -> List[str]:
        """Validate CSV row locally before API calls"""
        errors = []
        
        # Check required fields
        if not row.get('Name', '').strip():
            errors.append('Name is required')
        
        # Check folder path
        folder_path = row.get('Folder path', '').strip()
        if not folder_path:
            errors.append('Folder path is required')
        else:
            folder = Path(folder_path)
            if not folder.exists():
                errors.append(f'Folder does not exist: {folder_path}')
            elif not folder.is_dir():
                errors.append(f'Not a directory: {folder_path}')
            else:
                # Check for image files
                image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif',
                                  '*.JPG', '*.JPEG', '*.PNG', '*.GIF']
                image_files = []
                for ext in image_extensions:
                    image_files.extend(folder.glob(ext))
                
                if not image_files:
                    errors.append(f'No image files found in: {folder_path}')
        
        return errors
    
    def import_row(self, row: Dict, row_num: int, verbose: bool = False) -> Tuple[bool, str]:
        """Import single CSV row with all its images"""
        name = row.get('Name', '').strip()
        publisher = row.get('Publisher', '').strip()
        range_name = row.get('Range', '').strip()
        folder_path = row.get('Folder path', '').strip()
        
        # Check for duplicate
        is_dup, dup_id = self.check_duplicate(name, publisher, range_name)
        if is_dup:
            return False, f"⊘ Skipped duplicate: {name}"
        
        # Create entry
        success, entry_id, message = self.create_entry(row)
        if not success:
            return False, f"✗ Failed to create entry: {message}"
        
        if verbose:
            print(f"    Created entry: {name} (ID: {entry_id})")
        
        # Upload images from folder
        folder = Path(folder_path)
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif',
                          '*.JPG', '*.JPEG', '*.PNG', '*.GIF']
        image_files = []
        for ext in image_extensions:
            image_files.extend(folder.glob(ext))
        
        # Sort alphabetically
        image_files = sorted(image_files)
        
        uploaded_count = 0
        failed_count = 0
        
        for idx, image_path in enumerate(image_files):
            is_primary = (idx == 0)
            success, result = self.upload_image(entry_id, image_path, is_primary)
            
            if success:
                uploaded_count += 1
                if verbose:
                    primary_marker = ' (primary)' if is_primary else ''
                    print(f"      Uploaded: {result}{primary_marker}")
            else:
                failed_count += 1
                if verbose:
                    print(f"      Failed: {image_path.name} - {result}")
        
        if failed_count > 0:
            return True, f"✓ Created {name} with {uploaded_count}/{len(image_files)} images ({failed_count} failed)"
        else:
            return True, f"✓ Created {name} with {uploaded_count} images"


def main():
    parser = argparse.ArgumentParser(
        description='STL Collection Bulk CSV Import (Standalone)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test CSV validation
  python bulk_import_standalone.py import.csv --url http://localhost:8000 --username admin --password pass --test
  
  # Import to local server
  python bulk_import_standalone.py import.csv --url http://localhost:8000 --username admin --password pass
  
  # Import to remote server with verbose output
  python bulk_import_standalone.py import.csv --url https://server.com --username admin --password pass --verbose
        """
    )
    
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--url', required=True, help='Base URL of STL Collection (e.g., http://localhost:8000)')
    parser.add_argument('--username', required=True, help='Staff username')
    parser.add_argument('--password', required=True, help='Password')
    parser.add_argument('--test', action='store_true', help='Test mode (validation only, no API writes)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output showing detailed progress')
    
    args = parser.parse_args()
    
    # Print header
    print("=" * 70)
    print("STL Collection Bulk CSV Import (Standalone)")
    print("=" * 70)
    print()
    
    # Initialize importer
    importer = STLCollectionImporter(args.url, args.username, args.password)
    
    # Test connection
    print("Testing connection...")
    if not importer.health_check():
        print("\n✗ Cannot connect to server. Please check:")
        print("  - URL is correct and server is running")
        print("  - Username and password are correct")
        print("  - User has staff permissions")
        sys.exit(1)
    
    print()
    
    # Read CSV file
    if not os.path.exists(args.csv_file):
        print(f"✗ CSV file not found: {args.csv_file}")
        sys.exit(1)
    
    print(f"Reading CSV file: {args.csv_file}")
    rows = []
    
    try:
        with open(args.csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            # Verify required columns
            required_columns = ['Name', 'Folder path', 'Publisher', 'Range', 
                              'Faction Tag', 'Army Role', 'GW Alternative']
            
            if not reader.fieldnames:
                print("✗ CSV file is empty or has no header row")
                sys.exit(1)
            
            missing_columns = set(required_columns) - set(reader.fieldnames)
            if missing_columns:
                print(f"✗ CSV is missing required columns: {', '.join(missing_columns)}")
                sys.exit(1)
            
            for idx, row in enumerate(reader, start=2):
                row['_row_number'] = idx
                rows.append(row)
                
    except Exception as e:
        print(f"✗ Error reading CSV file: {e}")
        sys.exit(1)
    
    print(f"✓ Read {len(rows)} rows from CSV\n")
    
    if args.test:
        # TEST MODE - Validate only
        print("TEST MODE - Validating CSV")
        print("-" * 70)
        print()
        
        validation_errors = {}
        duplicates = []
        valid_count = 0
        
        # Fetch existing tags from server
        print("Fetching existing tags from server...")
        existing_tags = importer.get_existing_tags()
        print(f"✓ Found {sum(len(tags) for tags in existing_tags.values())} existing tags across {len(existing_tags)} tag types\n")
        
        # Collect all tags from CSV
        csv_tags = {
            'Publisher': set(),
            'Faction Tag': set(),
            'Army Role': set(),
            'GW Alternative': set()
        }
        
        for row in rows:
            row_num = row['_row_number']
            
            # Collect tags from this row
            if row.get('Publisher', '').strip():
                csv_tags['Publisher'].add(row['Publisher'].strip())
            if row.get('Faction Tag', '').strip():
                csv_tags['Faction Tag'].add(row['Faction Tag'].strip())
            if row.get('Army Role', '').strip():
                csv_tags['Army Role'].add(row['Army Role'].strip())
            gw_alt = row.get('GW Alternative', '').strip()
            if gw_alt:
                for tag in gw_alt.split(';'):
                    if tag.strip():
                        csv_tags['GW Alternative'].add(tag.strip())
            
            # Local validation
            errors = importer.validate_row(row, row_num)
            
            if errors:
                validation_errors[row_num] = errors
            else:
                # Check for remote duplicates
                name = row.get('Name', '').strip()
                publisher = row.get('Publisher', '').strip()
                range_name = row.get('Range', '').strip()
                
                is_dup, dup_id = importer.check_duplicate(name, publisher, range_name)
                if is_dup:
                    duplicates.append((row_num, name, publisher, range_name))
                else:
                    valid_count += 1
        
        # Display validation errors
        if validation_errors:
            print("VALIDATION ERRORS:")
            print()
            for row_num, errors in sorted(validation_errors.items()):
                print(f"Row {row_num}:")
                for error in errors:
                    print(f"  - {error}")
                print()
        
        # Display duplicates
        if duplicates:
            print("DUPLICATES (will be skipped):")
            print()
            for row_num, name, pub, rng in duplicates:
                print(f"  Row {row_num}: {name}")
                print(f"    Publisher: {pub or 'N/A'}, Range: {rng or 'N/A'}")
            print()
        
        # Identify and display new tags
        new_tags = {}
        for tag_type, csv_tag_set in csv_tags.items():
            if csv_tag_set:  # Only check if there are tags of this type
                existing_tag_set = set(existing_tags.get(tag_type, []))
                new_tag_set = csv_tag_set - existing_tag_set
                if new_tag_set:
                    new_tags[tag_type] = sorted(new_tag_set)
        
        if new_tags:
            print("NEW TAGS TO BE CREATED:")
            print()
            for tag_type, tags in sorted(new_tags.items()):
                print(f"  {tag_type}:")
                for tag in tags:
                    print(f"    - {tag}")
            print()
        
        # Summary
        print("=" * 70)
        print("SUMMARY:")
        print()
        print(f"  Total rows in CSV:     {len(rows)}")
        print(f"  Valid entries:         {valid_count}")
        print(f"  Duplicates to skip:    {len(duplicates)}")
        print(f"  Rows with errors:      {len(validation_errors)}")
        total_new_tags = sum(len(tags) for tags in new_tags.values())
        print(f"  New tags to create:    {total_new_tags}")
        print()
        
        if validation_errors:
            print("✗ Validation failed. Please fix errors before running import.")
            sys.exit(1)
        else:
            print("✓ Validation passed! Ready for import.")
            print()
            print("Run without --test flag to perform actual import:")
            print(f"  python bulk_import_standalone.py {args.csv_file} --url {args.url} --username {args.username} --password ****")
    
    else:
        # IMPORT MODE - Actually create entries
        print("IMPORT MODE - Creating entries and uploading images")
        print("-" * 70)
        print()
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for idx, row in enumerate(rows, start=1):
            row_num = row['_row_number']
            name = row.get('Name', '').strip()
            
            if args.verbose:
                print(f"Processing row {idx}/{len(rows)} (CSV row {row_num})...")
            
            # Validate locally first
            errors = importer.validate_row(row, row_num)
            if errors:
                print(f"✗ Row {row_num}: Validation failed")
                for error in errors:
                    print(f"    {error}")
                error_count += 1
                continue
            
            # Import the row
            success, message = importer.import_row(row, row_num, args.verbose)
            
            if not args.verbose:
                print(f"Row {row_num}: {message}")
            else:
                print(f"  {message}")
            
            if "Skipped duplicate" in message:
                skip_count += 1
            elif success:
                success_count += 1
            else:
                error_count += 1
        
        # Final summary
        print()
        print("=" * 70)
        print("FINAL SUMMARY:")
        print()
        print(f"  Total rows processed:      {len(rows)}")
        print(f"  Successfully created:      {success_count}")
        print(f"  Skipped duplicates:        {skip_count}")
        print(f"  Failed with errors:        {error_count}")
        print()
        
        if error_count == 0:
            print("✓ Import completed successfully!")
        else:
            print("⚠ Import completed with some errors.")
            print("  Check the output above for details.")


if __name__ == '__main__':
    main()
