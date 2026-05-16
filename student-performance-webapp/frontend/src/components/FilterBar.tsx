import { Filter, X } from "lucide-react";

interface FilterBarProps {
  filters: { [key: string]: string }; //options (branch, semester,year..)
  options: { [key: string]: string[] }; //aptions in the filter sciences math ...
  onChange: (key: string, value: string) => void; //fn passed from parent when user picks a value parent updates state
  onClear: () => void; //fn passed from parent when user click Réinitialiser parent resets all filters
  config: { key: string; label: string; optionsKey?: string }[];
  //config is a list of filter definitions used to build the UI dynamically
  //[ ] means it's an array of objects
}

export default function FilterBar({ filters, options, onChange, onClear, config }: FilterBarProps) {
  //check if any filter is active
  const hasActiveFilters = Object.values(filters).some(v => v !== "");
  //the .some(v => v !== "") Returns true if at least one value is not empty. This decides whether to show the "Réinitialiser" button.

  return (
    <div className="bg-white rounded-2xl shadow-lg p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-gray-700">
          <Filter size={18} />
          <span className="font-semibold">Filtres</span>
        </div>
        {hasActiveFilters && ( //only show the clear button if at least one filter is active (&&)
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
        {config.map(({ key, label, optionsKey }) => { //loop through the cofig array (for each item a dropdown)
          // Use optionsKey if provided, otherwise fall back to key
          const lookupKey = optionsKey ?? key;
          const dropdownOptions = options[lookupKey] || [];

          return (
            <div key={key}>
              <label className="block text-xs text-gray-500 mb-1">{label}</label>
              <select
                value={filters[key] || ""} //he dropdown shows the current filter value. If none, show empty (which maps to "Tous").
                onChange={(e) => onChange(key, e.target.value)} //when user picks smth call the parent's onChange with key(which filer eg branch) and e.target.value (what was picked example eco)
                className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary"
              >
                <option value="">Tous</option> {/*if empty Tous */}
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