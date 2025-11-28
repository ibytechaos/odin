"use client";

import { useState } from "react";

interface Field {
  name: string;
  type: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
  options?: string[];
}

interface FormRendererProps {
  title?: string;
  fields?: Field[];
  submitLabel?: string;
}

export function FormRenderer({
  title = "Form",
  fields = [],
  submitLabel = "Submit",
}: FormRendererProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);

  const handleChange = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Form submitted:", formData);
    setSubmitted(true);
    // In a real app, this would send data to the backend
    alert(
      `Form submitted!\n\nData:\n${JSON.stringify(formData, null, 2)}\n\nIn a real app, this would be sent to the backend.`
    );
  };

  if (submitted) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
        <div className="text-green-600 text-2xl mb-2">✓</div>
        <p className="text-green-800 font-medium">Form submitted successfully!</p>
        <button
          onClick={() => {
            setSubmitted(false);
            setFormData({});
          }}
          className="mt-3 text-sm text-green-600 hover:underline"
        >
          Submit another
        </button>
      </div>
    );
  }

  const renderField = (field: Field) => {
    const label = field.label || field.name.replace(/_/g, " ");
    const baseInputClass =
      "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all";

    switch (field.type) {
      case "textarea":
        return (
          <textarea
            name={field.name}
            placeholder={field.placeholder || `Enter ${label.toLowerCase()}`}
            required={field.required}
            value={formData[field.name] || ""}
            onChange={(e) => handleChange(field.name, e.target.value)}
            className={`${baseInputClass} min-h-[100px] resize-y`}
          />
        );

      case "select":
        return (
          <select
            name={field.name}
            required={field.required}
            value={formData[field.name] || ""}
            onChange={(e) => handleChange(field.name, e.target.value)}
            className={baseInputClass}
          >
            <option value="">Select {label.toLowerCase()}</option>
            {field.options?.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        );

      case "checkbox":
        return (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              name={field.name}
              checked={formData[field.name] === "true"}
              onChange={(e) =>
                handleChange(field.name, e.target.checked ? "true" : "false")
              }
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">{label}</span>
          </label>
        );

      default:
        return (
          <input
            type={field.type || "text"}
            name={field.name}
            placeholder={field.placeholder || `Enter ${label.toLowerCase()}`}
            required={field.required}
            value={formData[field.name] || ""}
            onChange={(e) => handleChange(field.name, e.target.value)}
            className={baseInputClass}
          />
        );
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 max-w-md">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">{title}</h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        {fields.map((field) => (
          <div key={field.name}>
            {field.type !== "checkbox" && (
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.label || field.name.replace(/_/g, " ")}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>
            )}
            {renderField(field)}
          </div>
        ))}

        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors"
        >
          {submitLabel}
        </button>
      </form>
    </div>
  );
}
