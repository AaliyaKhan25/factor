import { InputHTMLAttributes } from "react";

export const fieldClass =
  "min-h-11 w-full rounded-xl border border-line bg-white px-3 text-base text-ink placeholder:text-stone-400 focus:border-brand-dark focus:outline-none focus:ring-2 focus:ring-brand/60";

export default function Input({
  label,
  hint,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-stone-700">{label}</span>
      <input {...props} className={fieldClass} />
      {hint ? <span className="mt-1 block text-xs text-stone-500">{hint}</span> : null}
    </label>
  );
}
