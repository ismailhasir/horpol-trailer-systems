interface Props<T extends { id: string; label: string }> {
  label: string;
  options: T[];
  value: string;
  onChange: (id: string) => void;
}

/** Az seçenek varsa segment butonlar, çoksa açılır liste. */
export function OptionGroup<T extends { id: string; label: string }>({ label, options, value, onChange }: Props<T>) {
  if (options.length > 4) {
    return (
      <label className="field">
        <span className="field-label">{label}</span>
        <select value={value} onChange={(e) => onChange(e.target.value)}>
          {options.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
    );
  }
  return (
    <fieldset className="field">
      <legend className="field-label">{label}</legend>
      <div className="segmented" role="radiogroup">
        {options.map((o) => (
          <button
            key={o.id}
            type="button"
            role="radio"
            aria-checked={o.id === value}
            className={o.id === value ? "seg active" : "seg"}
            onClick={() => onChange(o.id)}
          >
            {o.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
