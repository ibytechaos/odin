"use client";

interface ProgressRendererProps {
  label?: string;
  current?: number;
  total?: number;
  percentage?: number;
  status?: "in_progress" | "completed" | "error";
}

export function ProgressRenderer({
  label = "Progress",
  current = 0,
  total = 100,
  percentage = 0,
  status = "in_progress",
}: ProgressRendererProps) {
  const getStatusColor = () => {
    switch (status) {
      case "completed":
        return "bg-green-500";
      case "error":
        return "bg-red-500";
      default:
        return "bg-blue-500";
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case "completed":
        return "✓";
      case "error":
        return "✕";
      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-sm text-gray-500">
          {current} / {total}
        </span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${getStatusColor()}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      <div className="flex items-center justify-between mt-2">
        <span className="text-lg font-semibold text-gray-800">
          {percentage}%
        </span>
        {status !== "in_progress" && (
          <span
            className={`flex items-center gap-1 text-sm ${
              status === "completed" ? "text-green-600" : "text-red-600"
            }`}
          >
            {getStatusIcon()}{" "}
            {status === "completed" ? "Completed" : "Error"}
          </span>
        )}
      </div>
    </div>
  );
}
