"""
Mock API Server for Telegram AI Listings - SQLite Version
Mimics the original croller.bsite.net API endpoints
"""

from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from flask_cors import CORS
from flasgger import Swagger
import sqlite3
from datetime import datetime, timedelta
import os
from pathlib import Path
from werkzeug.utils import secure_filename
import logging

# Import crawler service
from crawler_service import crawler_service

app = Flask(__name__)
CORS(app)

# Swagger configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/"
}

swagger_template = {
    "info": {
        "title": "Telegram AI Crawler API",
        "description": "API for storing and retrieving Telegram channel listings",
        "version": "1.0.0"
    },
    "basePath": "/",
    "schemes": ["http"]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
DATABASE = 'telegram_listings.db'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    """Create database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database with schema and sample data"""
    conn = get_db_connection()
    cur = conn.cursor()

    # Create tables
    cur.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            user_name TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            channel_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS listing_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            original_filename TEXT,
            file_size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
        )
    ''')

    # Create indexes
    cur.execute('CREATE INDEX IF NOT EXISTS idx_listings_username ON listings(user_name)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_listings_created ON listings(created_at DESC)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_listing_images_listing ON listing_images(listing_id)')

    # Check if we need to insert sample data
    cur.execute('SELECT COUNT(*) as count FROM listings')
    if cur.fetchone()['count'] == 0:
        # Insert sample data
        sample_listings = [
            ('Brand new iPhone 15 Pro Max 256GB, sealed box. Price negotiable. Contact for details.', 'tech_deals_uz', 12345, 'tech_deals_uz'),
            ('Samsung Galaxy S24 Ultra, excellent condition, comes with original charger and case.', 'gadget_store', 12346, 'gadget_store'),
            ('MacBook Air M2 2024, 16GB RAM, 512GB SSD. Like new, under warranty.', 'laptop_market', 12347, 'laptop_market')
        ]
        cur.executemany(
            'INSERT INTO listings (description, user_name, message_id, channel_username) VALUES (?, ?, ?, ?)',
            sample_listings
        )

        # Insert sample images
        sample_images = [
            (1, 'uploads/listing_1_img_1.jpg', 'iphone15pro.jpg', None),
            (1, 'uploads/listing_1_img_2.jpg', 'iphone15pro_box.jpg', None),
            (2, 'uploads/listing_2_img_1.jpg', 'galaxy_s24.jpg', None),
            (3, 'uploads/listing_3_img_1.jpg', 'macbook_air.jpg', None),
            (3, 'uploads/listing_3_img_2.jpg', 'macbook_specs.jpg', None)
        ]
        cur.executemany(
            'INSERT INTO listing_images (listing_id, image_path, original_filename, file_size) VALUES (?, ?, ?, ?)',
            sample_images
        )
        logger.info("Sample data inserted successfully")

    conn.commit()
    conn.close()

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint
    ---
    tags:
      - System
    responses:
      200:
        description: Server is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
            database:
              type: string
              example: connected
      500:
        description: Server is unhealthy
    """
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/api/Crawler', methods=['POST'])
def create_listing():
    """Create a new listing from Telegram
    ---
    tags:
      - Listings
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - description
            - userName
            - messageId
          properties:
            description:
              type: string
              example: "iPhone 15 Pro Max for sale, excellent condition"
            userName:
              type: string
              example: "tech_deals_uz"
            messageId:
              type: integer
              example: 12345
    responses:
      200:
        description: Listing created successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            description:
              type: string
            user_name:
              type: string
            message_id:
              type: integer
            created_at:
              type: string
      400:
        description: Missing required fields
      500:
        description: Server error
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data or not all(k in data for k in ('description', 'userName', 'messageId')):
            return jsonify({'error': 'Missing required fields: description, userName, messageId'}), 400

        description = data.get('description')
        user_name = data.get('userName')
        message_id = data.get('messageId')

        # Insert into database
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            '''
            INSERT INTO listings (description, user_name, message_id, channel_username)
            VALUES (?, ?, ?, ?)
            ''',
            (description, user_name, message_id, user_name)
        )

        listing_id = cur.lastrowid
        conn.commit()

        # Fetch the created listing
        cur.execute(
            'SELECT id, description, user_name, message_id, created_at FROM listings WHERE id = ?',
            (listing_id,)
        )
        listing = dict(cur.fetchone())
        conn.close()

        logger.info(f"Created listing {listing['id']} from @{user_name} (message {message_id})")

        return jsonify(listing), 200

    except Exception as e:
        logger.error(f"Error creating listing: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/Crawler/listing/images', methods=['POST'])
def upload_listing_images():
    """Upload images for a listing
    ---
    tags:
      - Images
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: listingId
        type: integer
        required: true
        description: ID of the listing
      - in: formData
        name: ListingImages
        type: file
        required: true
        description: Image file to upload (jpg, png, gif, webp)
    responses:
      200:
        description: Image uploaded successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            image_id:
              type: integer
            filename:
              type: string
      400:
        description: Missing listingId or file
      500:
        description: Server error
    """
    try:
        # Check if listingId is present
        if 'listingId' not in request.form:
            return jsonify({'error': 'Missing listingId'}), 400

        listing_id = int(request.form['listingId'])

        # Check if file is present
        if 'ListingImages' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['ListingImages']

        # Check if file is valid
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400

        # Secure the filename and save
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"listing_{listing_id}_{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        file.save(filepath)
        file_size = os.path.getsize(filepath)

        # Insert into database
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            '''
            INSERT INTO listing_images (listing_id, image_path, original_filename, file_size)
            VALUES (?, ?, ?, ?)
            ''',
            (listing_id, filepath, filename, file_size)
        )

        image_id = cur.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Uploaded image {image_id} for listing {listing_id}: {unique_filename}")

        return jsonify({
            'success': True,
            'message': 'Image uploaded successfully',
            'image_id': image_id,
            'filename': unique_filename
        }), 200

    except ValueError:
        return jsonify({'error': 'Invalid listingId format'}), 400
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/Crawler/listings', methods=['GET'])
def get_listings():
    """Get all listings with pagination
    ---
    tags:
      - Listings
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
        description: Page number
      - in: query
        name: per_page
        type: integer
        default: 10
        description: Items per page
    responses:
      200:
        description: List of listings
        schema:
          type: object
          properties:
            total:
              type: integer
            page:
              type: integer
            per_page:
              type: integer
            listings:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  description:
                    type: string
                  user_name:
                    type: string
                  message_id:
                    type: integer
                  image_count:
                    type: integer
                  created_at:
                    type: string
      500:
        description: Server error
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        offset = (page - 1) * per_page

        conn = get_db_connection()
        cur = conn.cursor()

        # Get total count
        cur.execute("SELECT COUNT(*) as count FROM listings")
        total = cur.fetchone()['count']

        # Get listings with image counts
        cur.execute(
            '''
            SELECT l.*, COUNT(li.id) as image_count
            FROM listings l
            LEFT JOIN listing_images li ON l.id = li.listing_id
            GROUP BY l.id
            ORDER BY l.created_at DESC
            LIMIT ? OFFSET ?
            ''',
            (per_page, offset)
        )

        listings = [dict(row) for row in cur.fetchall()]
        conn.close()

        return jsonify({
            'total': total,
            'page': page,
            'per_page': per_page,
            'listings': listings
        }), 200

    except Exception as e:
        logger.error(f"Error getting listings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/Crawler/listings/<int:listing_id>', methods=['GET'])
def get_listing_details(listing_id):
    """Get detailed listing with images
    ---
    tags:
      - Listings
    parameters:
      - in: path
        name: listing_id
        type: integer
        required: true
        description: Listing ID
    responses:
      200:
        description: Listing details with images
      404:
        description: Listing not found
      500:
        description: Server error
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get listing
        cur.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
        listing = cur.fetchone()

        if not listing:
            return jsonify({'error': 'Listing not found'}), 404

        listing = dict(listing)

        # Get images
        cur.execute(
            "SELECT * FROM listing_images WHERE listing_id = ? ORDER BY created_at",
            (listing_id,)
        )
        images = [dict(row) for row in cur.fetchall()]

        conn.close()

        listing['images'] = images

        return jsonify(listing), 200

    except Exception as e:
        logger.error(f"Error getting listing details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def dashboard():
    """Serve admin dashboard"""
    return render_template('dashboard.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    """Serve uploaded images"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/Crawler/statistics', methods=['GET'])
def get_statistics():
    """Get system statistics
    ---
    tags:
      - Statistics
    responses:
      200:
        description: System statistics
        schema:
          type: object
          properties:
            total_listings:
              type: integer
            unique_channels:
              type: integer
            total_images:
              type: integer
            today_listings:
              type: integer
      500:
        description: Server error
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Total listings
        cur.execute('SELECT COUNT(*) as count FROM listings')
        total_listings = cur.fetchone()['count']

        # Unique channels
        cur.execute('SELECT COUNT(DISTINCT user_name) as count FROM listings')
        unique_channels = cur.fetchone()['count']

        # Total images
        cur.execute('SELECT COUNT(*) as count FROM listing_images')
        total_images = cur.fetchone()['count']

        # Today's listings
        today = datetime.now().date()
        cur.execute(
            "SELECT COUNT(*) as count FROM listings WHERE DATE(created_at) = ?",
            (today,)
        )
        today_listings = cur.fetchone()['count']

        conn.close()

        return jsonify({
            'total_listings': total_listings,
            'unique_channels': unique_channels,
            'total_images': total_images,
            'today_listings': today_listings
        }), 200

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/Crawler/channel-stats', methods=['GET'])
def get_channel_stats():
    """Get statistics per channel
    ---
    tags:
      - Statistics
    responses:
      200:
        description: Channel statistics
        schema:
          type: object
          properties:
            channels:
              type: array
              items:
                type: object
                properties:
                  channel_name:
                    type: string
                  listing_count:
                    type: integer
                  image_count:
                    type: integer
                  last_activity:
                    type: string
      500:
        description: Server error
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('''
            SELECT
                l.user_name as channel_name,
                COUNT(DISTINCT l.id) as listing_count,
                COUNT(li.id) as image_count,
                MAX(l.created_at) as last_activity
            FROM listings l
            LEFT JOIN listing_images li ON l.id = li.listing_id
            GROUP BY l.user_name
            ORDER BY listing_count DESC
        ''')

        channels = [dict(row) for row in cur.fetchall()]
        conn.close()

        return jsonify({'channels': channels}), 200

    except Exception as e:
        logger.error(f"Error getting channel stats: {e}")
        return jsonify({'error': str(e)}), 500

# =============================================================================
# CSV Export Endpoints
# =============================================================================

@app.route('/api/csv-export/channels', methods=['GET'])
def get_available_channels():
    """Get list of available channels from schemas
    ---
    tags:
      - CSV Export
    responses:
      200:
        description: List of available channels
        schema:
          type: object
          properties:
            channels:
              type: array
              items:
                type: object
                properties:
                  username:
                    type: string
                    example: "baburieltor"
                  schema:
                    type: string
                    example: "real_estate"
            total:
              type: integer
      500:
        description: Server error
    """
    try:
        channels = crawler_service.get_available_channels()
        return jsonify({
            'channels': channels,
            'total': len(channels)
        }), 200
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/csv-export/schemas', methods=['GET'])
def get_available_schemas():
    """Get list of available schemas
    ---
    tags:
      - CSV Export
    responses:
      200:
        description: List of available schemas
        schema:
          type: object
          properties:
            schemas:
              type: array
              items:
                type: object
                properties:
                  name:
                    type: string
                  description:
                    type: string
                  channels:
                    type: array
                  channel_count:
                    type: integer
      500:
        description: Server error
    """
    try:
        schemas = crawler_service.get_schemas()
        return jsonify({'schemas': schemas}), 200
    except Exception as e:
        logger.error(f"Error getting schemas: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/csv-export/start', methods=['POST'])
def start_csv_export():
    """Start a new CSV export crawl job
    ---
    tags:
      - CSV Export
    parameters:
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            channels:
              type: array
              items:
                type: string
              description: List of channel usernames (empty = all channels)
              example: ["baburieltor", "realtor_alii"]
            messages_per_channel:
              type: integer
              default: 10
              description: Number of messages to fetch per channel
              example: 20
    responses:
      200:
        description: Crawl job started
        schema:
          type: object
          properties:
            job_id:
              type: string
            status:
              type: string
            channels:
              type: array
            message:
              type: string
      400:
        description: Invalid request or job already running
      500:
        description: Server error
    """
    try:
        data = request.get_json() or {}
        channels = data.get('channels', [])
        messages_per_channel = data.get('messages_per_channel', 10)

        # Validate
        if not isinstance(messages_per_channel, int) or messages_per_channel < 1:
            return jsonify({'error': 'messages_per_channel must be a positive integer'}), 400

        if messages_per_channel > 100:
            return jsonify({'error': 'messages_per_channel cannot exceed 100'}), 400

        # Start crawl
        job = crawler_service.start_crawl(
            channels=channels if channels else None,
            messages_per_channel=messages_per_channel
        )

        logger.info(f"Started crawl job {job.job_id} with {len(job.channels)} channels")

        return jsonify({
            'job_id': job.job_id,
            'status': job.status,
            'channels': job.channels,
            'messages_per_channel': job.messages_per_channel,
            'message': f'Crawl job started with {len(job.channels)} channels'
        }), 200

    except RuntimeError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error starting crawl: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/csv-export/status', methods=['GET'])
def get_csv_export_status():
    """Get current crawl job status
    ---
    tags:
      - CSV Export
    parameters:
      - in: query
        name: job_id
        type: string
        required: false
        description: Specific job ID (optional, defaults to current job)
    responses:
      200:
        description: Job status
        schema:
          type: object
          properties:
            job_id:
              type: string
            status:
              type: string
              enum: [pending, running, completed, failed, stopped]
            current_channel:
              type: string
            progress_percent:
              type: integer
            stats:
              type: object
            recent_logs:
              type: array
      404:
        description: No job found
      500:
        description: Server error
    """
    try:
        job_id = request.args.get('job_id')

        if job_id:
            job = crawler_service.get_job(job_id)
        else:
            job = crawler_service.get_current_job()

        if not job:
            return jsonify({
                'error': 'No crawl job found',
                'is_running': False
            }), 404

        return jsonify(job.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/csv-export/stop', methods=['POST'])
def stop_csv_export():
    """Stop the current crawl job
    ---
    tags:
      - CSV Export
    responses:
      200:
        description: Stop requested
        schema:
          type: object
          properties:
            message:
              type: string
            success:
              type: boolean
      400:
        description: No job running
      500:
        description: Server error
    """
    try:
        success = crawler_service.stop_crawl()

        if success:
            return jsonify({
                'success': True,
                'message': 'Stop requested. Job will stop after current operation.'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'No crawl job is currently running'
            }), 400

    except Exception as e:
        logger.error(f"Error stopping crawl: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/csv-export/download', methods=['GET'])
def download_csv():
    """Download the CSV file
    ---
    tags:
      - CSV Export
    responses:
      200:
        description: CSV file download
        content:
          text/csv:
            schema:
              type: string
              format: binary
      404:
        description: CSV file not found
      500:
        description: Server error
    """
    try:
        csv_path = crawler_service.get_csv_path()

        if not csv_path or not os.path.exists(csv_path):
            return jsonify({'error': 'CSV file not found. Run a crawl first.'}), 404

        return send_file(
            csv_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name='real_estate_listings.csv'
        )

    except Exception as e:
        logger.error(f"Error downloading CSV: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/csv-export/output-stats', methods=['GET'])
def get_output_stats():
    """Get statistics about output files
    ---
    tags:
      - CSV Export
    responses:
      200:
        description: Output statistics
        schema:
          type: object
          properties:
            csv_exists:
              type: boolean
            csv_path:
              type: string
            csv_size:
              type: integer
            images_count:
              type: integer
            images_size:
              type: integer
      500:
        description: Server error
    """
    try:
        stats = crawler_service.get_output_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting output stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/csv-export/jobs', methods=['GET'])
def get_all_jobs():
    """Get all crawl jobs history
    ---
    tags:
      - CSV Export
    responses:
      200:
        description: List of all jobs
        schema:
          type: object
          properties:
            jobs:
              type: array
            total:
              type: integer
      500:
        description: Server error
    """
    try:
        jobs = crawler_service.get_all_jobs()
        return jsonify({
            'jobs': [job.to_dict() for job in jobs],
            'total': len(jobs)
        }), 200
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/csv-export/images/<path:filename>')
def serve_csv_export_images(filename):
    """Serve images from CSV export output
    ---
    tags:
      - CSV Export
    parameters:
      - in: path
        name: filename
        type: string
        required: true
        description: Image filename
    responses:
      200:
        description: Image file
      404:
        description: Image not found
    """
    images_dir = Path(__file__).parent.parent / 'crawler' / 'output' / 'images'
    return send_from_directory(str(images_dir), filename)


@app.route('/api/csv-export/listings', methods=['GET'])
def get_csv_listings():
    """Get listings from CSV file
    ---
    tags:
      - CSV Export
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
        description: Page number
      - in: query
        name: per_page
        type: integer
        default: 20
        description: Items per page
      - in: query
        name: channel
        type: string
        required: false
        description: Filter by channel username
      - in: query
        name: search
        type: string
        required: false
        description: Search in raw_text field
    responses:
      200:
        description: List of CSV listings
        schema:
          type: object
          properties:
            total:
              type: integer
            page:
              type: integer
            per_page:
              type: integer
            listings:
              type: array
      404:
        description: CSV file not found
      500:
        description: Server error
    """
    import csv

    try:
        csv_path = crawler_service.get_csv_path()

        if not csv_path or not os.path.exists(csv_path):
            return jsonify({
                'error': 'CSV file not found. Run a crawl first.',
                'listings': [],
                'total': 0
            }), 404

        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        channel_filter = request.args.get('channel', '').strip()
        search_query = request.args.get('search', '').strip().lower()

        listings = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Apply channel filter
                if channel_filter and row.get('channel', '') != channel_filter:
                    continue

                # Apply search filter
                if search_query:
                    raw_text = row.get('raw_text', '').lower()
                    if search_query not in raw_text:
                        continue

                # Parse image paths
                image_paths_str = row.get('image_paths', '')
                image_paths = [p.strip() for p in image_paths_str.split(';') if p.strip()]

                listings.append({
                    'id': int(row.get('listing_id', 0)),
                    'channel': row.get('channel', ''),
                    'message_id': int(row.get('message_id', 0)),
                    'timestamp': row.get('timestamp', ''),
                    'rooms': row.get('rooms', ''),
                    'price': row.get('price', ''),
                    'currency': row.get('currency', ''),
                    'area_m2': row.get('area_m2', ''),
                    'floor': row.get('floor', ''),
                    'total_floors': row.get('total_floors', ''),
                    'district': row.get('district', ''),
                    'address': row.get('address', ''),
                    'property_type': row.get('property_type', ''),
                    'deal_type': row.get('deal_type', ''),
                    'condition': row.get('condition', ''),
                    'phone_numbers': row.get('phone_numbers', ''),
                    'raw_text': row.get('raw_text', ''),
                    'image_paths': image_paths,
                    'image_count': len(image_paths)
                })

        # Sort by ID descending (newest first)
        listings.sort(key=lambda x: x['id'], reverse=True)

        # Apply pagination
        total = len(listings)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = listings[start:end]

        # Get unique channels for filter dropdown
        all_channels = list(set(l['channel'] for l in listings))
        all_channels.sort()

        return jsonify({
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'listings': paginated,
            'channels': all_channels
        }), 200

    except Exception as e:
        logger.error(f"Error reading CSV listings: {e}")
        return jsonify({'error': str(e)}), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Initializing Telegram AI API Server (SQLite)...")
    init_database()
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"Database: {DATABASE}")
    logger.info("Server running on http://localhost:5002")
    app.run(host='0.0.0.0', port=5002, debug=True)
