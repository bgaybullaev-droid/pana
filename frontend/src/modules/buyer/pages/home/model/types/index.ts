/** F048 — top-of-home tab identifiers (Лента / Подписки / Рекомендуемое). */
export type HomeTab = "feed" | "subscriptions" | "recommended";

/** Sorting option ids as shown in the filter drawer chips. */
export type HomeSort = "recommended" | "newest" | "cheapest" | "expensive";

export interface HomeFilters {
  q?: string;
  type?: ('sell' | 'rent')[];
  property_type?: ('apartment' | 'house' | 'commercial' | 'land')[];
  rooms?: number[];
  price_min?: number;
  price_max?: number;
  region?: string[];
  district?: string[];
  /** Applied feed ordering; undefined = default relevance ("recommended"). */
  sort?: Exclude<HomeSort, "recommended">;

  // --- Wave-1 attribute filters (all server-backed at /listings/feed) ---
  area_min?: number;
  area_max?: number;
  floor_min?: number;
  floor_max?: number;
  total_floors_min?: number;
  total_floors_max?: number;
  not_first_floor?: boolean;
  not_last_floor?: boolean;
  /** "new" | "secondary". */
  building_type?: "new" | "secondary";
  condition?: string[];
  has_photo?: boolean;
  /** Freshness window in days (1 | 7 | 30). */
  posted_within?: number;

  // --- Deal-terms filters (platform-only) ---
  mortgage_ok?: boolean;
  installment_ok?: boolean;
  halol_ok?: boolean;
  furnished?: boolean;
  allowed_pets?: boolean;
  allowed_students?: boolean;
  utilities_incl?: boolean;
  rent_period?: "long_term" | "daily";
}
