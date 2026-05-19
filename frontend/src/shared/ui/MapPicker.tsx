import { FC, useEffect, useRef, useState } from "react";
import { Box, ActionIcon, Group, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { IconMaximize, IconMinimize, IconMapPin } from "@tabler/icons-react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface MapPickerProps {
	lat: number | null;
	lng: number | null;
	onChange: (lat: number, lng: number) => void;
	onAddressResolved?: (address: string) => void;
	/** External center override — map pans here when this changes (e.g. region/district selection) */
	centerLat?: number | null;
	centerLng?: number | null;
	centerZoom?: number;
	height?: number;
}

// Default center: Tashkent
const DEFAULT_CENTER: [number, number] = [41.311, 69.279];

async function reverseGeocode(lat: number, lng: number): Promise<string> {
	try {
		const res = await fetch(
			`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&accept-language=uz,ru`,
		);
		if (!res.ok) return "";
		const data = await res.json();
		return data.display_name || "";
	} catch {
		return "";
	}
}

export const MapPicker: FC<MapPickerProps> = ({
	lat,
	lng,
	onChange,
	onAddressResolved,
	centerLat,
	centerLng,
	centerZoom,
	height = 220,
}) => {
	const { t } = useTranslation("common");
	const containerRef = useRef<HTMLDivElement>(null);
	const mapRef = useRef<L.Map | null>(null);
	const markerRef = useRef<L.Marker | null>(null);
	const [fullscreen, setFullscreen] = useState(false);

	const center: [number, number] = lat && lng ? [lat, lng] : DEFAULT_CENTER;
	const hasMarker = lat != null && lng != null;
	const geocodeTimerRef = useRef<ReturnType<typeof setTimeout>>();

	const handlePositionChange = (newLat: number, newLng: number) => {
		onChange(newLat, newLng);
		if (onAddressResolved) {
			// Debounce geocoding to avoid spamming the API during drags
			if (geocodeTimerRef.current) clearTimeout(geocodeTimerRef.current);
			geocodeTimerRef.current = setTimeout(() => {
				reverseGeocode(newLat, newLng).then((addr) => {
					if (addr) onAddressResolved(addr);
				});
			}, 500);
		}
	};

	useEffect(() => {
		if (!containerRef.current) return;

		// Destroy previous map if exists
		if (mapRef.current) {
			mapRef.current.remove();
			mapRef.current = null;
			markerRef.current = null;
		}

		const map = L.map(containerRef.current, {
			center,
			zoom: hasMarker ? 15 : 12,
			zoomControl: false,
			attributionControl: false,
		});

		L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
			maxZoom: 19,
		}).addTo(map);

		L.control.zoom({ position: "bottomright" }).addTo(map);

		// Place marker if coordinates exist
		if (hasMarker) {
			const icon = L.divIcon({
				html: `<div style="
          width: 28px; height: 28px;
          background: #228be6;
          border: 3px solid white;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        "></div>`,
				iconSize: [28, 28],
				iconAnchor: [14, 28],
				className: "",
			});
			markerRef.current = L.marker(center, { icon, draggable: true }).addTo(
				map,
			);
			markerRef.current.on("dragend", () => {
				const pos = markerRef.current!.getLatLng();
				handlePositionChange(pos.lat, pos.lng);
			});
		}

		// Click to place/move marker
		map.on("click", (e: L.LeafletMouseEvent) => {
			const { lat: clickLat, lng: clickLng } = e.latlng;

			if (markerRef.current) {
				markerRef.current.setLatLng(e.latlng);
			} else {
				const icon = L.divIcon({
					html: `<div style="
            width: 28px; height: 28px;
            background: #228be6;
            border: 3px solid white;
            border-radius: 50% 50% 50% 0;
            transform: rotate(-45deg);
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
          "></div>`,
					iconSize: [28, 28],
					iconAnchor: [14, 28],
					className: "",
				});
				markerRef.current = L.marker(e.latlng, { icon, draggable: true }).addTo(
					map,
				);
				markerRef.current.on("dragend", () => {
					const pos = markerRef.current!.getLatLng();
					onChange(pos.lat, pos.lng);
				});
			}

			handlePositionChange(clickLat, clickLng);
		});

		mapRef.current = map;

		// Fix map size after render
		setTimeout(() => map.invalidateSize(), 100);

		return () => {
			map.remove();
			mapRef.current = null;
			markerRef.current = null;
		};
	}, [fullscreen]); // Re-create map on fullscreen toggle

	// Update marker position when lat/lng props change externally
	// (e.g. async data load on edit page)
	useEffect(() => {
		if (!mapRef.current || lat == null || lng == null) return;

		if (markerRef.current) {
			// Existing marker — update position
			markerRef.current.setLatLng([lat, lng]);
		} else {
			// First time receiving coords — create marker
			const icon = L.divIcon({
				html: `<div style="
          width: 28px; height: 28px;
          background: #228be6;
          border: 3px solid white;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        "></div>`,
				iconSize: [28, 28],
				iconAnchor: [14, 28],
				className: "",
			});
			markerRef.current = L.marker([lat, lng], {
				icon,
				draggable: true,
			}).addTo(mapRef.current);
			markerRef.current.on("dragend", () => {
				const pos = markerRef.current!.getLatLng();
				handlePositionChange(pos.lat, pos.lng);
			});
		}
		mapRef.current.setView([lat, lng], mapRef.current.getZoom());
	}, [lat, lng]);

	// Pan map when external center changes (region/district selection)
	useEffect(() => {
		if (!mapRef.current || !centerLat || !centerLng) return;
		mapRef.current.setView([centerLat, centerLng], centerZoom || 13, {
			animate: true,
			duration: 0.5,
		});
	}, [centerLat, centerLng, centerZoom]);

	const toggleFullscreen = () => setFullscreen((prev) => !prev);

	return (
		<Box
			style={
				fullscreen
					? {
							position: "fixed",
							top: 0,
							left: 0,
							right: 0,
							bottom: 0,
							zIndex: 10000,
							background: "white",
							padding: 0,
						}
					: { position: "relative" }
			}
		>
			{/* Header bar in fullscreen */}
			{fullscreen && (
				<Box px="md" py="sm" style={{ borderBottom: "1px solid #e9ecef" }}>
					<Group justify="space-between">
						<Group gap={6}>
							<IconMapPin size={18} color="#228be6" />
							<Text fw={600} size="sm">
								{t("map.selectLocation")}
							</Text>
						</Group>
						<ActionIcon variant="subtle" onClick={toggleFullscreen}>
							<IconMinimize size={18} />
						</ActionIcon>
					</Group>
				</Box>
			)}

			<Box style={{ position: "relative" }}>
				<Box
					ref={containerRef}
					style={{
						height: fullscreen ? "calc(100vh - 50px)" : height,
						width: "100%",
						borderRadius: fullscreen ? 0 : 12,
						overflow: "hidden",
						border: fullscreen ? "none" : "1px solid #e9ecef",
					}}
				/>

				{/* Fullscreen toggle (only in non-fullscreen) */}
				{!fullscreen && (
					<ActionIcon
						variant="filled"
						size={32}
						radius="md"
						onClick={toggleFullscreen}
						style={{
							position: "absolute",
							top: 8,
							right: 8,
							zIndex: 1000,
							backgroundColor: "rgba(255,255,255,0.9)",
							color: "#333",
							boxShadow: "0 2px 6px rgba(0,0,0,0.15)",
						}}
					>
						<IconMaximize size={16} />
					</ActionIcon>
				)}
			</Box>

			{/* Coordinates display */}
			{hasMarker && (
				<Text size="xs" c="dimmed" mt={4}>
					{lat!.toFixed(5)}, {lng!.toFixed(5)}
				</Text>
			)}
		</Box>
	);
};
