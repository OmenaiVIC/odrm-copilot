import { ReactNode } from 'react';

interface FieldProps {
  label: string;
  unit?: string;
  id: string;
  type?: string;
  value: string | number;
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void;
  error?: string | null;
  required?: boolean;
  children?: ReactNode; // For select dropdowns
}

export function Field({
  label,
  unit,
  id,
  type = 'number',
  value,
  onChange,
  error,
  required = true,
  children,
}: FieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {label} {unit && <span className="text-xs text-gray-400 font-normal">({unit})</span>}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      {children ? (
        children
      ) : (
        <input
          id={id}
          type={type}
          value={value}
          onChange={onChange}
          className={`rounded-lg border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-700 dark:text-white ${
            error ? 'border-red-500 focus:ring-red-500' : 'border-gray-300'
          }`}
          step="any"
        />
      )}
      
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  );
}