import { FC, useEffect, useRef } from "react";
import { Box } from "@mantine/core";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { UnifiedListing } from "@shared/api/types";

// Coordinates for Uzbekistan regions and cities
const LOCATION_COORDS: Record<string, [number, number]> = {
	// Regions
	tashkent: [41.311, 69.279],
	samarkand: [39.654, 66.959],
	bukhara: [39.774, 64.421],
	fergana: [40.384, 71.789],
	andijan: [40.783, 72.344],
	namangan: [41.0, 71.672],
	navoi: [40.103, 65.379],
	kashkadarya: [38.86, 65.8],
	surkhandarya: [37.224, 67.278],
	jizzakh: [40.119, 67.842],
	syrdarya: [40.838, 68.665],
	khorezm: [41.553, 60.631],
	karakalpakstan: [42.461, 59.6],
	// Tashkent districts
	mirobod: [41.306, 69.274],
	chilanzar: [41.262, 69.187],
	yashnabad: [41.288, 69.331],
	yakkasaray: [41.291, 69.266],
	sergeli: [41.21, 69.232],
	sergeliy: [41.21, 69.232],
	uchtepa: [41.312, 69.192],
	almazar: [41.337, 69.222],
	bektemir: [41.212, 69.326],
	mirzo_ulugbek: [41.352, 69.335],
	shaykhontohur: [41.332, 69.243],
	yunusabad: [41.37, 69.279],
	// Cities
	nukus: [42.461, 59.6],
	urgench: [41.553, 60.631],
	termez: [37.224, 67.278],
	karshi: [38.86, 65.8],
	gulistan: [40.838, 68.665],
};

// All known location keywords mapped to coordinate keys
const ALL_KEYWORDS: [string, string][] = [
	// English / Latin district names
	["sergeliy", "sergeli"],
	["sergeli", "sergeli"],
	["mirobod", "mirobod"],
	["mirzo_ulugbek", "mirzo_ulugbek"],
	["mirzo ulugbek", "mirzo_ulugbek"],
	["yakkasaroy", "yakkasaray"],
	["yakkasaray", "yakkasaray"],
	["yunusobod", "yunusabad"],
	["yunusabad", "yunusabad"],
	["chilanzar", "chilanzar"],
	["uchtepa", "uchtepa"],
	["almazar", "almazar"],
	["bektemir", "bektemir"],
	["shaykhontohur", "shaykhontohur"],
	["yashnabad", "yashnabad"],
	// Russian district names
	["сергели", "sergeli"],
	["мирабад", "mirobod"],
	["мирзо", "mirzo_ulugbek"],
	["яккасарай", "yakkasaray"],
	["юнусабад", "yunusabad"],
	["чиланзар", "chilanzar"],
	["учтепа", "uchtepa"],
	["алмазар", "almazar"],
	["бектемир", "bektemir"],
	["шайхонтохур", "shaykhontohur"],
	["яшнабад", "yashnabad"],
	// Region / city names (less specific — checked last)
	["buxoro", "bukhara"],
	["bukhara", "bukhara"],
	["бухар", "bukhara"],
	["samarqand", "samarkand"],
	["samarkand", "samarkand"],
	["самарканд", "samarkand"],
	["fergana", "fergana"],
	["ферган", "fergana"],
	["andijan", "andijan"],
	["андижан", "andijan"],
	["namangan", "namangan"],
	["наманган", "namangan"],
	["navoi", "navoi"],
	["навои", "navoi"],
	["kashkadarya", "kashkadarya"],
	["кашкадарь", "kashkadarya"],
	["surkhandarya", "surkhandarya"],
	["сурхандарь", "surkhandarya"],
	["jizzakh", "jizzakh"],
	["джизак", "jizzakh"],
	["khorezm", "khorezm"],
	["хорезм", "khorezm"],
	["karakalpakstan", "karakalpakstan"],
	["каракалпак", "karakalpakstan"],
	["nukus", "nukus"],
	["нукус", "nukus"],
	["tashkent", "tashkent"],
	["toshkent", "tashkent"],
	["ташкент", "tashkent"],
];

function matchField(fieldValue: string | null): [number, number] | null {
	if (!fieldValue) return null;
	const text = fieldValue.toLowerCase();
	for (const [keyword, coordKey] of ALL_KEYWORDS) {
		if (text.includes(keyword)) {
			return LOCATION_COORDS[coordKey] || null;
		}
	}
	return null;
}

export function getListingCoords(
	listing: UnifiedListing,
): { lat: number; lng: number; exact: boolean } | null {
	// 1. Use exact coordinates from backend if available
	if (listing.latitude && listing.longitude) {
		return { lat: listing.latitude, lng: listing.longitude, exact: true };
	}

	// 2. Search fields in priority order: most specific first
	// District is the most precise, then address, then region, then raw text
	const fieldsInOrder = [
		listing.district,
		listing.address,
		listing.region,
		listing.description,
		listing.raw_text,
	];

	for (const field of fieldsInOrder) {
		const coords = matchField(field);
		if (coords) {
			const hasSpecificAddress = listing.address && listing.address.length > 10;
			return { lat: coords[0], lng: coords[1], exact: !!hasSpecificAddress };
		}
	}

	return null;
}

interface ListingMapProps {
	lat: number;
	lng: number;
	exact: boolean;
	height?: number;
}

export const ListingMap: FC<ListingMapProps> = ({
	lat,
	lng,
	exact,
	height = 300,
}) => {
	const containerRef = useRef<HTMLDivElement>(null);
	const mapRef = useRef<L.Map | null>(null);

	useEffect(() => {
		if (!containerRef.current || mapRef.current) return;

		const map = L.map(containerRef.current, {
			center: [lat, lng],
			zoom: exact ? 16 : 13,
			zoomControl: false,
			attributionControl: false,
			dragging: true,
			scrollWheelZoom: false,
		});

		L.control.zoom({ position: "bottomright" }).addTo(map);

		L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
			maxZoom: 19,
		}).addTo(map);

		if (exact) {
			const icon = L.divIcon({
				html: `<div style="
          width: 32px; height: 32px;
          background: #228be6;
          border: 3px solid white;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        "></div>`,
				iconSize: [32, 32],
				iconAnchor: [16, 32],
				className: "",
			});
			L.marker([lat, lng], { icon }).addTo(map);
		} else {
			L.circle([lat, lng], {
				radius: 1500,
				color: "#228be6",
				fillColor: "#228be6",
				fillOpacity: 0.15,
				weight: 2,
			}).addTo(map);

			L.circleMarker([lat, lng], {
				radius: 6,
				color: "#228be6",
				fillColor: "#228be6",
				fillOpacity: 0.8,
				weight: 2,
			}).addTo(map);
		}

		mapRef.current = map;

		return () => {
			map.remove();
			mapRef.current = null;
		};
	}, [lat, lng, exact]);

	return (
		<Box
			ref={containerRef}
			style={{
				height,
				width: "100%",
				borderRadius: 12,
				overflow: "hidden",
			}}
		/>
	);
};
