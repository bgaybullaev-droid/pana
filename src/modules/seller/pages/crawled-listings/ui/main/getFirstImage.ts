export function getFirstImage(images: string[] | null): string | null {
  if (!images || images.length === 0) return null;
  const first = images[0];
  if (typeof first === 'string') return first;
  if (typeof first === 'object' && first !== null && 'url' in first) {
    return (first as { url: string }).url;
  }
  return null;
}
