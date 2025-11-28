"use client";

import { useState } from "react";

interface AlertRendererProps {
  type?: "info" | "success" | "warning" | "error";
  title?: string;
  message?: string;
  dismissable?: boolean;
}

export function AlertRenderer({
  type = "info",
  title,
  message = "",
  dismissable = true,
}: AlertRendererProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  const getTypeStyles = () => {
    switch (type) {
      case "success":
        return {
          bg: "bg-green-50",
          border: "border-green-200",
          icon: "✓",
          iconBg: "bg-green-100 text-green-600",
          title: "text-green-800",
          message: "text-green-700",
        };
      case "warning":
        return {
          bg: "bg-yellow-50",
          border: "border-yellow-200",
          icon: "⚠",
          iconBg: "bg-yellow-100 text-yellow-600",
          title: "text-yellow-800",
          message: "text-yellow-700",
        };
      case "error":
        return {
          bg: "bg-red-50",
          border: "border-red-200",
          icon: "✕",
          iconBg: "bg-red-100 text-red-600",
          title: "text-red-800",
          message: "text-red-700",
        };
      default: // info
        return {
          bg: "bg-blue-50",
          border: "border-blue-200",
          icon: "ℹ",
          iconBg: "bg-blue-100 text-blue-600",
          title: "text-blue-800",
          message: "text-blue-700",
        };
    }
  };

  const styles = getTypeStyles();

  return (
    <div
      className={`rounded-lg border p-4 ${styles.bg} ${styles.border}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${styles.iconBg}`}
        >
          {styles.icon}
        </div>

        <div className="flex-1">
          {title && (
            <h4 className={`font-semibold ${styles.title}`}>{title}</h4>
          )}
          <p className={`text-sm ${styles.message} ${title ? "mt-1" : ""}`}>
            {message}
          </p>
        </div>

        {dismissable && (
          <button
            onClick={() => setDismissed(true)}
            className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
