import { useState, useRef, useEffect } from "react";
import { Filter, X, ChevronDown } from "lucide-react";

interface FilterBarProps {
  filters: { [key: string]: string[] };
  options: { [key: string]: string[] };
  onChange: (key: string, value: string) => void;
  onClear: () => void;
  config: { key: string; label: string; optionsKey?: string }[];
}

export default function FilterBar({ filters, options, onChange, onClear, config }: FilterBarProps) {
  const [openKey, setOpenKey] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const hasActiveFilters = Object.values(filters).some((arr) => arr.length > 0);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpenKey(null);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="bg-white rounded-2xl shadow-lg p-4 mb-6" ref={containerRef}>
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
          const lookupKey = optionsKey ?? key;
          const dropdownOptions = options[lookupKey] || [];
          const selectedValues = filters[key] || [];
          const isOpen = openKey === key;

          return (
            <div key={key} className="relative">
              <label className="block text-xs text-gray-500 mb-1">
                {label}
                {selectedValues.length > 0 && (
                  <span className="ml-1 text-primary font-semibold">({selectedValues.length})</span>
                )}
              </label>

              {/* Trigger button */}
              <button
                type="button"
                onClick={() => setOpenKey(isOpen ? null : key)}
                className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl border text-sm bg-gray-50 hover:bg-gray-100 transition ${
                  isOpen ? "border-primary ring-1 ring-primary" : "border-gray-200"
                }`}
              >
                <span className="truncate text-gray-700">
                  {selectedValues.length === 0
                    ? "Tous"
                    : selectedValues.length === 1
                    ? selectedValues[0]
                    : `${selectedValues.length} sélectionnés`}
                </span>
                <ChevronDown
                  size={14}
                  className={`flex-shrink-0 text-gray-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
                />
              </button>

              {/* Dropdown panel */}
              {isOpen && (
                <div className="absolute z-50 mt-1 w-full min-w-max bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
                  {dropdownOptions.length === 0 ? (
                    <p className="text-xs text-gray-400 px-3 py-2">Aucune option</p>
                  ) : (
                    <div className="max-h-48 overflow-y-auto p-1">
                      {dropdownOptions.map((opt) => (
                        <label
                          key={opt}
                          className="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-gray-50 text-sm text-gray-700"
                        >
                          <input
                            type="checkbox"
                            checked={selectedValues.includes(opt)}
                            onChange={() => onChange(key, opt)}
                            className="accent-primary"
                          />
                          {opt}
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}