// Mirrors backend/app/filters.py — ids must match exactly; the backend
// validates them and returns a 422 on drift.

export interface FilterOption {
  id: string;
  label: string;
}

export const DOMAINS: FilterOption[] = [
  { id: "gaming", label: "Gaming" },
  { id: "finance", label: "Finance" },
  { id: "healthcare", label: "Healthcare" },
  { id: "education", label: "Education" },
  { id: "developer_tools", label: "Developer Tools" },
  { id: "social", label: "Social / Communication" },
  { id: "media", label: "Media / Entertainment" },
  { id: "science", label: "Science / Research" },
];

// Display-only emoji per domain id (not part of the backend mirror).
export const DOMAIN_ICONS: Record<string, string> = {
  gaming: "🎮",
  finance: "💰",
  healthcare: "🩺",
  education: "🎓",
  developer_tools: "🛠️",
  social: "💬",
  media: "🎬",
  science: "🔬",
};

export const SIZES: FilterOption[] = [
  { id: "small", label: "Small (< 5 MB)" },
  { id: "medium", label: "Medium (5–50 MB)" },
  { id: "large", label: "Large (> 50 MB)" },
];

export const STARS: FilterOption[] = [
  { id: "lt100", label: "< 100" },
  { id: "100-1k", label: "100 – 1k" },
  { id: "1k-10k", label: "1k – 10k" },
  { id: "gt10k", label: "> 10k" },
];

export const CONTRIBUTORS: FilterOption[] = [
  { id: "lt10", label: "< 10" },
  { id: "10-50", label: "10 – 50" },
  { id: "50-200", label: "50 – 200" },
  { id: "gt200", label: "> 200" },
];

// Mirrors backend/app/filters.py QUALITY_DEFINITIONS — same ids, same order.
// A mismatched id fails request validation, so change both together.
export const QUALITIES: FilterOption[] = [
  { id: "availability", label: "Availability" },
  { id: "security", label: "Security" },
  { id: "modifiability", label: "Modifiability" },
  { id: "performance", label: "Performance" },
  { id: "testability", label: "Testability" },
  { id: "usability", label: "Usability" },
  { id: "deployability", label: "Deployability" },
  { id: "energy_efficiency", label: "Energy Efficiency" },
];

// Fixed semantic tone per quality; anything unrecognised (an old cached label,
// say) falls back to neutral. Shared by the story card, the catalog, and the
// library so a quality reads the same colour everywhere.
export const QUALITY_TONE: Record<string, string> = Object.fromEntries(
  QUALITIES.map((q) => [q.id, `tag-${q.id.replace("_", "-")}`]),
);
