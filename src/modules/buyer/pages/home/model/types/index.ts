export interface HomeFilters {
  q?: string;
  type?: ('sell' | 'rent')[];
  property_type?: ('apartment' | 'house' | 'commercial' | 'land')[];
  rooms?: number[];
  price_min?: number;
  price_max?: number;
  region?: string[];
  district?: string[];
  
  // --- MOCKUP FILTERS (Visually working in Drawer, ignored by Server for now) ---
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
