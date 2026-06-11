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

  // --- MOCKUP FILTERS (hidden in the Drawer until /listings/feed supports them) ---
  area_min?: number;
  area_max?: number;
  building_type?: string[];
  condition?: string[];
  house_type?: string[];
  house_condition?: string[];
  furnished?: string[];
  amenities?: string[];
  water_supply?: string[];
  electricity?: string[];
  heating?: string[];
  gas_supply?: string[];
  sewage?: string[];
}
