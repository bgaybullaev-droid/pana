"""
CSV Exporter Utility for Real Estate Crawler
Handles CSV file operations and image saving
"""

import csv
import os
import threading
from pathlib import Path
from datetime import datetime


class CSVExporter:
    """Export real estate listings to CSV file"""

    # CSV column headers
    HEADERS = [
        'listing_id',
        'channel',
        'message_id',
        'timestamp',
        'property_type',
        'listing_type',
        'price',
        'currency',
        'rooms',
        'area_sqm',
        'floor',
        'total_floors',
        'district',
        'address',
        'description',
        'contact_phone',
        'amenities',
        'image_paths',
        'raw_text'
    ]

    def __init__(self, output_dir='output'):
        """
        Initialize CSV exporter

        Args:
            output_dir: Directory for output files (default: 'output')
        """
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / 'images'
        self.csv_path = self.output_dir / 'real_estate_listings.csv'

        # Thread-safe lock for CSV writing
        self._lock = threading.Lock()

        # Current listing ID counter
        self._current_id = 0

        # Initialize directories and CSV
        self._init_directories()
        self._init_csv()

    def _init_directories(self):
        """Create output directories if they don't exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        print(f"[CSV] Output directory: {self.output_dir.absolute()}")
        print(f"[CSV] Images directory: {self.images_dir.absolute()}")

    def _init_csv(self):
        """Initialize CSV file with headers or resume from existing"""
        if self.csv_path.exists():
            # Resume from existing CSV - find last listing_id
            self._current_id = self._get_last_id()
            print(f"[CSV] Resuming from existing CSV, last ID: {self._current_id}")
        else:
            # Create new CSV with headers
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.HEADERS)
            print(f"[CSV] Created new CSV file: {self.csv_path}")

    def _get_last_id(self):
        """Get the last listing_id from existing CSV"""
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                last_id = 0
                for row in reader:
                    try:
                        listing_id = int(row.get('listing_id', 0))
                        if listing_id > last_id:
                            last_id = listing_id
                    except (ValueError, TypeError):
                        continue
                return last_id
        except Exception as e:
            print(f"[CSV] Error reading existing CSV: {e}")
            return 0

    def get_next_id(self):
        """Get next auto-incremented listing ID"""
        with self._lock:
            self._current_id += 1
            return self._current_id

    def clean_text(self, text, max_length=500):
        """
        Clean text for CSV compatibility

        Args:
            text: Input text
            max_length: Maximum length (default: 500)

        Returns:
            Cleaned text string
        """
        if not text:
            return ''

        # Convert to string
        text = str(text)

        # Replace newlines with spaces
        text = text.replace('\n', ' ').replace('\r', ' ')

        # Replace multiple spaces with single space
        while '  ' in text:
            text = text.replace('  ', ' ')

        # Strip whitespace
        text = text.strip()

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length - 3] + '...'

        return text

    def format_amenities(self, amenities):
        """
        Format amenities list to comma-separated string

        Args:
            amenities: List of amenities or string

        Returns:
            Comma-separated string
        """
        if not amenities:
            return ''

        if isinstance(amenities, list):
            return ', '.join(str(a) for a in amenities if a)

        return str(amenities)

    def get_image_filename(self, listing_id, image_index=1):
        """
        Generate image filename

        Args:
            listing_id: Listing ID
            image_index: Image number (1, 2, 3...)

        Returns:
            Filename string (e.g., 'listing_00001_img_1.jpg')
        """
        return f"listing_{listing_id:05d}_img_{image_index}.jpg"

    def get_image_path(self, listing_id, image_index=1):
        """
        Get full path for saving image

        Args:
            listing_id: Listing ID
            image_index: Image number

        Returns:
            Full Path object
        """
        filename = self.get_image_filename(listing_id, image_index)
        return self.images_dir / filename

    def get_relative_image_path(self, listing_id, image_index=1):
        """
        Get relative image path for CSV

        Args:
            listing_id: Listing ID
            image_index: Image number

        Returns:
            Relative path string (e.g., 'images/listing_00001_img_1.jpg')
        """
        filename = self.get_image_filename(listing_id, image_index)
        return f"images/{filename}"

    def save_row(self, listing_id, channel, message_id, timestamp, extracted_data, image_paths, raw_text):
        """
        Save a single listing row to CSV

        Args:
            listing_id: Auto-generated listing ID
            channel: Telegram channel username
            message_id: Telegram message ID
            timestamp: Message timestamp (datetime or ISO string)
            extracted_data: Dict with extracted fields from LLM
            image_paths: List of relative image paths
            raw_text: Original message text
        """
        # Format timestamp
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()

        # Extract fields from LLM data
        row = [
            listing_id,
            channel,
            message_id,
            timestamp,
            extracted_data.get('property_type', ''),
            extracted_data.get('listing_type', ''),
            extracted_data.get('price', ''),
            extracted_data.get('currency', ''),
            extracted_data.get('rooms', ''),
            extracted_data.get('area_sqm', ''),
            extracted_data.get('floor', ''),
            extracted_data.get('total_floors', ''),
            extracted_data.get('district', ''),
            self.clean_text(extracted_data.get('address', ''), max_length=200),
            self.clean_text(extracted_data.get('description', ''), max_length=500),
            extracted_data.get('contact_phone', ''),
            self.format_amenities(extracted_data.get('amenities', [])),
            ';'.join(image_paths) if image_paths else '',
            self.clean_text(raw_text, max_length=1000)
        ]

        # Thread-safe write
        with self._lock:
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)

        print(f"[CSV] Saved listing #{listing_id} from @{channel}")

    def is_duplicate(self, channel, message_id):
        """
        Check if message already exists in CSV

        Args:
            channel: Channel username
            message_id: Telegram message ID

        Returns:
            True if duplicate, False otherwise
        """
        if not self.csv_path.exists():
            return False

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('channel') == channel and str(row.get('message_id')) == str(message_id):
                        return True
        except Exception:
            pass

        return False

    def get_stats(self):
        """
        Get statistics about exported data

        Returns:
            Dict with stats
        """
        stats = {
            'total_listings': 0,
            'channels': set(),
            'total_images': 0
        }

        if not self.csv_path.exists():
            return stats

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stats['total_listings'] += 1
                    stats['channels'].add(row.get('channel', ''))

                    # Count images
                    image_paths = row.get('image_paths', '')
                    if image_paths:
                        stats['total_images'] += len(image_paths.split(';'))

            stats['unique_channels'] = len(stats['channels'])
            stats['channels'] = list(stats['channels'])

        except Exception as e:
            print(f"[CSV] Error getting stats: {e}")

        return stats


# Test the exporter
if __name__ == '__main__':
    print("Testing CSV Exporter...")

    exporter = CSVExporter(output_dir='test_output')

    # Test save_row
    test_data = {
        'property_type': 'apartment',
        'listing_type': 'sale',
        'price': 85000,
        'currency': 'USD',
        'rooms': 3,
        'area_sqm': 75.5,
        'floor': 5,
        'total_floors': 9,
        'district': 'Chilonzor',
        'address': 'Chilonzor 7-kvartal',
        'description': 'Beautiful apartment with modern renovation',
        'contact_phone': '+998901234567',
        'amenities': ['gas', 'hot_water', 'parking']
    }

    listing_id = exporter.get_next_id()
    exporter.save_row(
        listing_id=listing_id,
        channel='test_channel',
        message_id=12345,
        timestamp=datetime.now(),
        extracted_data=test_data,
        image_paths=['images/listing_00001_img_1.jpg'],
        raw_text='Test message text with\nnewlines and   spaces'
    )

    print(f"\nStats: {exporter.get_stats()}")
    print(f"\nCSV file created at: {exporter.csv_path}")
