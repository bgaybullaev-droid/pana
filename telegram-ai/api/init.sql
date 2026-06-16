-- Database initialization script for Telegram AI Listings

CREATE TABLE IF NOT EXISTS listings (
    id SERIAL PRIMARY KEY,
    description TEXT NOT NULL,
    user_name VARCHAR(255) NOT NULL,
    message_id BIGINT NOT NULL,
    channel_username VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS listing_images (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL,
    image_path VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255),
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

CREATE INDEX idx_listings_username ON listings(user_name);
CREATE INDEX idx_listings_created ON listings(created_at DESC);
CREATE INDEX idx_listing_images_listing ON listing_images(listing_id);

-- Insert sample data for testing
INSERT INTO listings (description, user_name, message_id, channel_username) VALUES
('Brand new iPhone 15 Pro Max 256GB, sealed box. Price negotiable. Contact for details.', 'tech_deals_uz', 12345, 'tech_deals_uz'),
('Samsung Galaxy S24 Ultra, excellent condition, comes with original charger and case.', 'gadget_store', 12346, 'gadget_store'),
('MacBook Air M2 2024, 16GB RAM, 512GB SSD. Like new, under warranty.', 'laptop_market', 12347, 'laptop_market');

-- Insert sample images (placeholder paths)
INSERT INTO listing_images (listing_id, image_path, original_filename) VALUES
(1, 'uploads/listing_1_img_1.jpg', 'iphone15pro.jpg'),
(1, 'uploads/listing_1_img_2.jpg', 'iphone15pro_box.jpg'),
(2, 'uploads/listing_2_img_1.jpg', 'galaxy_s24.jpg'),
(3, 'uploads/listing_3_img_1.jpg', 'macbook_air.jpg'),
(3, 'uploads/listing_3_img_2.jpg', 'macbook_specs.jpg');

COMMENT ON TABLE listings IS 'Product listings crawled from Telegram channels';
COMMENT ON TABLE listing_images IS 'Images associated with product listings';
