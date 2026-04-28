import { Filter, X } from "lucide-react";

interface FilterBarProps {
  filters: { [key: string]: string };
  options: { [key: string]: string[] };
  onChange: (key: string, value: string) => void;
  onClear: () => void;
  config: { key: string; label: string; optionsKey?: string }[];
}

export default function FilterBar({ filters, options, onChange, onClear, config }: FilterBarProps) {
  const hasActiveFilters = Object.values(filters).some(v => v !== "");

  return (
    <div className="bg-white rounded-2xl shadow-lg p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-gray-700">
          <Filter size={18} />
          <span className="font-semibold">Filtres</span>
        </div>
        {hasActiveFilters && (
          <button
            onClick={onClear}
            className="flex items-center gap-1 text-sm text-red-500 hover:text-red-600"
          >
            <X size={14} />
            Réinitialiser
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {config.map(({ key, label, optionsKey }) => {
          // Use optionsKey if provided, otherwise fall back to key
          const lookupKey = optionsKey ?? key;
          const dropdownOptions = options[lookupKey] || [];

          return (
            <div key={key}>
              <label className="block text-xs text-gray-500 mb-1">{label}</label>
              <select
                value={filters[key] || ""}
                onChange={(e) => onChange(key, e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary"
              >
                <option value="">Tous</option>
                {dropdownOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      </div>
    </div>
  );
}