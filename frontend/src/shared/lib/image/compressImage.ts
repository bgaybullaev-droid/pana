/**
 * Client-side image normalisation before upload.
 *
 * Phone cameras (especially iOS) hand back HEIC files or 12–40 MP JPEGs.
 * The backend `/uploads/image` endpoint only accepts jpeg/png/webp up to
 * 10 MB and rejects everything else with a 400 — and the form silently
 * dropped the rejected file from the grid, so sellers saw "not all photos
 * uploaded".
 *
 * This downscales the image to a sane max edge and re-encodes it to JPEG,
 * which both (a) converts HEIC/PNG/WebP into an accepted format and (b)
 * brings any oversized photo comfortably under the 10 MB cap. The browser
 * applies EXIF orientation when it renders the <img>, so the canvas copy
 * comes out upright.
 *
 * Decoding goes through the platform image pipeline, so HEIC works on iOS
 * (Telegram's WKWebView, where the system codec is present). If a file
 * cannot be decoded (e.g. HEIC on Android Chrome) or anything else throws,
 * the original file is returned unchanged — the result is never worse than
 * skipping compression entirely.
 */

export interface CompressImageOptions {
	/** Longest-edge cap in pixels. Larger images are scaled down to fit. */
	maxDimension?: number;
	/** JPEG encode quality, 0–1. */
	quality?: number;
}

const DEFAULT_MAX_DIMENSION = 1920;
const DEFAULT_QUALITY = 0.82;

const ACCEPTED_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp"];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // mirrors backend uploads.py

export async function compressImage(
	file: File,
	options: CompressImageOptions = {},
): Promise<File> {
	// Only touch raster images; pass anything else (or empty input) through.
	if (!file.type.startsWith("image/")) return file;

	const maxDimension = options.maxDimension ?? DEFAULT_MAX_DIMENSION;
	const quality = options.quality ?? DEFAULT_QUALITY;

	let objectUrl: string | null = null;
	try {
		objectUrl = URL.createObjectURL(file);
		const img = await loadImage(objectUrl);

		const width = img.naturalWidth || img.width;
		const height = img.naturalHeight || img.height;
		if (!width || !height) return file;

		const scale = Math.min(1, maxDimension / Math.max(width, height));
		const targetW = Math.max(1, Math.round(width * scale));
		const targetH = Math.max(1, Math.round(height * scale));

		const canvas = document.createElement("canvas");
		canvas.width = targetW;
		canvas.height = targetH;
		const ctx = canvas.getContext("2d");
		if (!ctx) return file;
		ctx.drawImage(img, 0, 0, targetW, targetH);

		const blob = await canvasToJpeg(canvas, quality);
		if (!blob) return file;

		// If the source is already an accepted format/size and re-encoding
		// didn't actually shrink it (tiny, pre-optimised JPEGs), keep the
		// original to avoid a needless quality round-trip.
		if (blob.size >= file.size && isBackendAcceptable(file)) return file;

		const baseName = file.name.replace(/\.[^./\\]+$/, "") || "photo";
		return new File([blob], `${baseName}.jpg`, {
			type: "image/jpeg",
			lastModified: Date.now(),
		});
	} catch {
		// Undecodable (e.g. HEIC on Android) or any other failure — fall back
		// to the original file so behaviour is never worse than before.
		return file;
	} finally {
		if (objectUrl) URL.revokeObjectURL(objectUrl);
	}
}

function isBackendAcceptable(file: File): boolean {
	return ACCEPTED_TYPES.includes(file.type) && file.size <= MAX_FILE_SIZE;
}

function loadImage(src: string): Promise<HTMLImageElement> {
	return new Promise((resolve, reject) => {
		const img = new Image();
		img.onload = () => resolve(img);
		img.onerror = () => reject(new Error("image decode failed"));
		img.src = src;
	});
}

function canvasToJpeg(
	canvas: HTMLCanvasElement,
	quality: number,
): Promise<Blob | null> {
	return new Promise((resolve) => {
		if (typeof canvas.toBlob === "function") {
			canvas.toBlob((b) => resolve(b), "image/jpeg", quality);
			return;
		}
		// Legacy WebViews without toBlob — fall back to toDataURL.
		try {
			resolve(dataUrlToBlob(canvas.toDataURL("image/jpeg", quality)));
		} catch {
			resolve(null);
		}
	});
}

function dataUrlToBlob(dataUrl: string): Blob {
	const [head, body] = dataUrl.split(",");
	const mime = head.match(/:(.*?);/)?.[1] ?? "image/jpeg";
	const binary = atob(body);
	const bytes = new Uint8Array(binary.length);
	for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
	return new Blob([bytes], { type: mime });
}
