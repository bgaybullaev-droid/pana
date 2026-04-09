// API Types

export interface PaginatedResponse<T> {
	items: T[];
	page: number;
	per_page: number;
	total: number;
	total_pages: number;
}

export interface MessageResponse {
	message: string;
	success: boolean;
}

// User types
export interface User {
	id: string;
	telegram_id: number;
	first_name: string;
	last_name: string | null;
	username: string | null;
	avatar_url: string | null;
	language: string;
	role: "user" | "seller" | "admin";
	onboarding_completed: boolean;
	created_at: string;
	updated_at: string;
}

export interface UserMeResponse {
	user_id: string;
	telegram_id: number | null;
	first_name: string;
	last_name: string | null;
	username: string | null;
	avatar_url: string | null;
	role: string;
	is_seller: boolean;
	onboarding_completed: boolean;
	approval_status: "pending" | "approved" | "rejected";
	auth_source: string | null;
	phone: string | null;
	scope: string | null;
}

export interface AuthResponse {
	user_id: string;
	telegram_id: number | null;
	first_name: string;
	last_name: string | null;
	username: string | null;
	avatar_url: string | null;
	role: string;
	is_seller: boolean;
	onboarding_completed: boolean;
	approval_status: "pending" | "approved" | "rejected";
	auth_source: string | null;
	phone: string | null;
	scope: string;
	access_token: string;
	refresh_token: string;
	token_type: string;
	expires_in: number;
}

// Listing types
export interface ListingImage {
	id: string;
	original_url: string;
	thumbnail_url: string | null;
	medium_url: string | null;
	large_url: string | null;
	position: number;
	is_primary: boolean;
}

export interface Listing {
	id: string;
	seller_id: string | null;
	type: "sell" | "rent";
	property_type: "apartment" | "house" | "commercial" | "land";
	rooms: number | null;
	area: number | null;
	floor: number | null;
	total_floors: number | null;
	region: string | null;
	district: string | null;
	address: string | null;
	latitude: number | null;
	longitude: number | null;
	price: number;
	currency: "USD" | "UZS";
	title: string | null;
	description: string | null;
	phone: string | null;
	living_area?: number | null;
	kitchen_area?: number | null;
	land_area?: number | null;
	building_type?: string | null;
	condition?: string | null;
	house_type?: string | null;
	house_condition?: string[] | null;
	location_type?: string[] | null;
	water_supply?: string[] | null;
	electricity?: string | null;
	heating?: string[] | null;
	gas_supply?: string | null;
	sewage?: string | null;
	is_furnished?: boolean | null;
	land_purpose?: string | null;
	amenities?: string[] | null;
	nearby_amenities?: string[] | null;
	seller_type?: string | null;
	is_negotiable?: boolean | null;
	source_type: "manual" | "claimed" | "parsed";
	status: "active" | "paused" | "sold" | "deleted" | "expired";
	moderation_status: "pending" | "approved" | "rejected";
	views_count: number;
	contacts_count: number;
	favorites_count: number;
	comments_count: number;
	is_boosted: boolean;
	boost_until: string | null;
	is_highlighted: boolean;
	created_at: string;
	updated_at: string;
	expires_at: string | null;
	images: ListingImage[];
	is_favorited?: boolean;
}

export interface ListingListItem {
	id: string;
	type: "sell" | "rent";
	property_type: "apartment" | "house" | "commercial" | "land";
	rooms: number | null;
	area: number | null;
	floor: number | null;
	total_floors: number | null;
	region: string | null;
	district: string | null;
	building_type: string | null;
	condition: string | null;
	land_purpose: string | null;
	price: number;
	currency: "USD" | "UZS";
	title: string | null;
	views_count: number;
	favorites_count: number;
	comments_count: number;
	is_boosted: boolean;
	is_highlighted: boolean;
	created_at: string;
	primary_image_url: string | null;
	is_favorited?: boolean;
}

export interface ListingFilters {
	q?: string;
	type?: "sell" | "rent";
	property_type?: "apartment" | "house" | "commercial" | "land";
	rooms?: number[];
	price_min?: number;
	price_max?: number;
	area_min?: number;
	area_max?: number;
	region?: string[];
	district?: string[];
	sort_by?: "created_at" | "price" | "area" | "views_count";
	sort_order?: "asc" | "desc";
}

// User preferences
export interface UserPreferences {
	regions: string[];
	districts: string[];
	property_types: string[];
	listing_types: string[];
	price_min: number | null;
	price_max: number | null;
	rooms: number[];
}

// Seller types
export interface Seller {
	id: string;
	user_id: string;
	company_name: string | null;
	description: string | null;
	logo_url: string | null;
	phone: string;
	email: string | null;
	phone_public: boolean;
	telegram_username: string | null;
	instagram_url: string | null;
	website_url: string | null;
	is_verified: boolean;
	verified_at: string | null;
	listings_count: number;
	total_views: number;
	total_contacts: number;
	created_at: string;
	updated_at: string;
}

export interface SellerPublic {
	id: string;
	company_name: string | null;
	description: string | null;
	logo_url: string | null;
	phone: string | null;
	telegram_username: string | null;
	instagram_url: string | null;
	website_url: string | null;
	is_verified: boolean;
	listings_count: number;
	created_at: string;
}

// Admin types
export interface AdminUser {
	id: string;
	telegram_id: number;
	phone: string | null;
	first_name: string;
	last_name: string | null;
	username: string | null;
	avatar_url: string | null;
	language: string;
	role: "user" | "seller" | "admin";
	approval_status: "pending" | "approved" | "rejected";
	approval_notes: string | null;
	approved_by: string | null;
	approved_at: string | null;
	onboarding_completed: boolean;
	created_at: string;
	updated_at: string;
}

export interface AdminUserListItem {
	id: string;
	telegram_id: number;
	phone: string | null;
	first_name: string;
	last_name: string | null;
	username: string | null;
	role: "user" | "seller" | "admin";
	approval_status: "pending" | "approved" | "rejected";
	created_at: string;
}

export interface AdminListingListItem {
	id: string;
	seller_id: string | null;
	seller_name: string | null;
	type: "sell" | "rent";
	property_type: "apartment" | "house" | "commercial" | "land";
	title: string | null;
	price: number;
	currency: "USD" | "UZS";
	region: string | null;
	district: string | null;
	source_type: "manual" | "claimed" | "parsed";
	moderation_status: "pending" | "approved" | "rejected";
	moderation_notes: string | null;
	created_at: string;
	primary_image_url: string | null;
}

export interface AdminListingDetail {
	id: string;
	seller_id: string | null;
	seller_name: string | null;
	seller_phone: string | null;
	type: "sell" | "rent";
	property_type: "apartment" | "house" | "commercial" | "land";
	rooms: number | null;
	area: number | null;
	floor: number | null;
	total_floors: number | null;
	region: string | null;
	district: string | null;
	address: string | null;
	latitude: number | null;
	longitude: number | null;
	price: number;
	currency: "USD" | "UZS";
	title: string | null;
	description: string | null;
	phone: string | null;
	source_type: "manual" | "claimed" | "parsed";
	source_url: string | null;
	raw_text: string | null;
	status: "active" | "paused" | "sold" | "deleted" | "expired";
	moderation_status: "pending" | "approved" | "rejected";
	moderation_notes: string | null;
	moderated_by: string | null;
	moderated_at: string | null;
	created_at: string;
	updated_at: string;
	images: ListingImage[];
}

export interface AdminDashboardStats {
	pending_users: number;
	total_users: number;
	pending_listings: number;
	total_listings: number;
	approved_users: number;
	rejected_users: number;
	approved_listings: number;
	rejected_listings: number;
}

// Notification preferences
export interface NotificationPreferences {
	enabled: boolean;
	time_start: string;
	time_end: string;
	timezone: string;
	daily_limit: number;
	districts: string[];
	property_types: string[];
	listing_types: string[];
	price_min: number | null;
	price_max: number | null;
	rooms: number[];
}

// Buyer Listings Types (TikTok-style UI)
export interface BuyerListingImage {
	imageUrl: string;
}

export interface BuyerListing {
	id: string;
	name: string;
	price: number;
	description: string;
	images: BuyerListingImage[];
	sellerUserName: string;
	sellerImage: string;
	likes?: number;
	isLiked?: boolean;
}

export interface BuyerListingsResponse {
	listings: BuyerListing[];
	listingsCount: number;
	currentPageNumber: number;
	nextPageNumber?: number;
}

export interface BuyerFilterState {
	sortingSelected: number; // -1 when not selected
	priceRange: [number, number]; // [minPrice, maxPrice]
	regions: string[]; // Array of region IDs
}

export interface SortingOption {
	id: number;
	label: string;
}

export interface Region {
	id: string;
	name: string;
}

export interface SearchHistoryItem {
	id: string;
	query: string;
	timestamp: number;
}

// Comment types
export interface CommentAuthor {
	id: string;
	first_name: string;
	last_name: string | null;
	username: string | null;
	avatar_url: string | null;
}

export interface Comment {
	id: string;
	listing_id: string;
	user_id: string;
	text: string;
	created_at: string;
	updated_at: string;
	author: CommentAuthor;
	replies_count: number;
	likes_count: number;
	is_liked?: boolean;
}

export interface CommentCreateRequest {
	text: string;
	parent_id?: string;
}

// Notification types
export type NotificationType =
	| "comment_reply"
	| "price_drop"
	| "new_listing"
	| "favorite_update";

export interface NotificationActor {
	id: string;
	first_name: string;
	last_name: string | null;
	username: string | null;
	avatar_url: string | null;
}

export interface Notification {
	id: string;
	user_id: string;
	type: NotificationType;
	title: string;
	message: string;
	listing_id: string | null;
	comment_id: string | null;
	actor: NotificationActor | null;
	read: boolean;
	created_at: string;
}

export interface NotificationMarkReadRequest {
	notification_ids?: string[];
}

export interface UnreadCountResponse {
	unread_count: number;
}

// Seller crawled stats
export interface SellerCrawledStats {
	olx_count: number;
	telegram_count: number;
	total_count: number;
}

// Crawler listing types

export interface TelegramListing {
	id: string;
	property_type: string;
	listing_type: string;
	price: number;
	currency: string;
	rooms: number | null;
	area_sqm: number | null;
	floor: number | null;
	total_floors: number | null;
	district: string | null;
	address: string | null;
	description: string | null;
	amenities: string[] | null;
	contact_phone: string | null;
	confidence: number | null;
	images: string[] | null;
	raw_text: string | null;
	source_channel: string | null;
	message_id: number | null;
	signature_hash: string | null;
	created_at: string;
	updated_at: string;
}

export interface OLXListing {
	id: string;
	olx_id: string;
	url: string;
	property_type: string;
	listing_type: string;
	price: number;
	currency: string;
	rooms: number | null;
	area_sqm: number | null;
	floor: number | null;
	total_floors: number | null;
	district: string | null;
	address: string | null;
	description: string | null;
	amenities: string[] | null;
	contact_phone: string | null;
	confidence: number | null;
	images: string[] | null;
	source: string;
	crawled_at: string;
	seller_type: string | null;
	seller_name: string | null;
	views_count: number | null;
	posted_date: string | null;
	building_type: string | null;
	condition: string | null;
	furnishing: string | null;
	ceiling_height: number | null;
	bathroom: string | null;
	raw_text: string | null;
	signature_hash: string | null;
	created_at: string;
	updated_at: string;
}

// Unified listing types (resolved from any source)

export interface UnifiedListingImage {
	url: string;
	thumbnail?: string | null;
}

export interface UnifiedListing {
	source: "main" | "telegram" | "olx";
	id: string;
	type: string;
	property_type: string;
	price: number;
	currency: string;
	rooms: number | null;
	area: number | null;
	floor: number | null;
	total_floors: number | null;
	region: string | null;
	district: string | null;
	address: string | null;
	latitude: number | null;
	longitude: number | null;
	description: string | null;
	raw_text: string | null;
	images: UnifiedListingImage[];
	contact_phone: string | null;
	created_at: string;

	// Main-only fields
	title: string | null;
	views_count: number;
	favorites_count: number;
	comments_count: number;
	is_favorited: boolean;
	is_boosted: boolean;
	is_highlighted: boolean;
	seller_id: string | null;
	seller_name: string | null;
	seller_avatar_url: string | null;
	seller_verified: boolean;

	// Crawler fields
	amenities: string[] | null;
	confidence: number | null;
	source_url: string | null;

	// Multilingual metadata
	original_language: string | null;
	is_translated: boolean;
}

export interface UnifiedListingListItem {
	id: string;
	source: "main" | "telegram" | "olx";
	type: string;
	property_type: string;
	price: number;
	currency: string;
	rooms: number | null;
	area: number | null;
	floor: number | null;
	total_floors: number | null;
	region: string | null;
	district: string | null;
	building_type: string | null;
	condition: string | null;
	land_purpose: string | null;
	primary_image_url: string | null;
	created_at: string;
}

export interface CrawlerListingFilters {
	property_type?: string;
	listing_type?: string;
	price_min?: number;
	price_max?: number;
	rooms?: number;
	district?: string;
	sort_by?: "created_at" | "price" | "area_sqm";
	sort_order?: "asc" | "desc";
	page?: number;
	per_page?: number;
}
