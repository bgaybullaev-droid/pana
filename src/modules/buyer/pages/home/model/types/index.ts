export interface HomeFilters {
  q?: string;
  type?: 'sell' | 'rent';
  property_type?: 'apartment' | 'house' | 'commercial' | 'land';
  rooms?: number[];
  price_min?: number;
  price_max?: number;
  region?: string[];
  district?: string[];
}
