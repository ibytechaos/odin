"use client";

import { useState } from "react";

interface TableRendererProps {
  title?: string;
  columns?: string[];
  rows?: Array<Record<string, any>>;
}

export function TableRenderer({
  title = "Table",
  columns = [],
  rows = [],
}: TableRendererProps) {
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  if (!rows || rows.length === 0) {
    return (
      <div className="p-4 bg-gray-100 rounded-lg text-center text-gray-500">
        No data available
      </div>
    );
  }

  // Get columns from first row if not provided
  const tableColumns = columns.length > 0 ? columns : Object.keys(rows[0]);

  // Sort rows
  const sortedRows = [...rows].sort((a, b) => {
    if (!sortColumn) return 0;
    const aVal = a[sortColumn];
    const bVal = b[sortColumn];

    if (typeof aVal === "number" && typeof bVal === "number") {
      return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
    }

    const aStr = String(aVal).toLowerCase();
    const bStr = String(bVal).toLowerCase();
    return sortDirection === "asc"
      ? aStr.localeCompare(bStr)
      : bStr.localeCompare(aStr);
  });

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const formatColumnName = (name: string) => {
    return name
      .replace(/_/g, " ")
      .replace(/([A-Z])/g, " $1")
      .trim()
      .split(" ")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  const formatCellValue = (value: any) => {
    if (value === null || value === undefined) return "-";
    if (typeof value === "boolean") return value ? "Yes" : "No";
    return String(value);
  };

  const getStatusColor = (status: string) => {
    const s = status.toLowerCase();
    if (s === "active" || s === "completed" || s === "success")
      return "bg-green-100 text-green-800";
    if (s === "inactive" || s === "failed" || s === "error")
      return "bg-red-100 text-red-800";
    if (s === "pending" || s === "in_progress")
      return "bg-yellow-100 text-yellow-800";
    return "bg-gray-100 text-gray-800";
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-800">{title}</h3>
        <p className="text-sm text-gray-500 mt-1">{rows.length} items</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              {tableColumns.map((column) => (
                <th
                  key={column}
                  onClick={() => handleSort(column)}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-1">
                    {formatColumnName(column)}
                    {sortColumn === column && (
                      <span>{sortDirection === "asc" ? "↑" : "↓"}</span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {sortedRows.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className="hover:bg-gray-50 transition-colors"
              >
                {tableColumns.map((column) => (
                  <td key={column} className="px-4 py-3 text-sm text-gray-700">
                    {column.toLowerCase() === "status" ? (
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                          row[column]
                        )}`}
                      >
                        {formatCellValue(row[column])}
                      </span>
                    ) : (
                      formatCellValue(row[column])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
