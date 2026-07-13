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

export const QUALITIES: FilterOption[] = [
  { id: "security", label: "Security" },
  { id: "performance", label: "Performance" },
  { id: "usability", label: "Usability" },
  { id: "maintainability", label: "Maintainability" },
];
