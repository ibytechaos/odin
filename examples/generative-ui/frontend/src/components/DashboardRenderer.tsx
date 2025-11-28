"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface DashboardRendererProps {
  metric?: string;
  current?: number;
  previous?: number;
  change?: number;
  trend?: "up" | "down" | "neutral";
  chart?: {
    type: string;
    data: Array<{ name: string; value: number }>;
  };
  insights?: string[];
}

export function DashboardRenderer({
  metric = "Metric",
  current = 0,
  previous = 0,
  change = 0,
  trend = "neutral",
  chart,
  insights = [],
}: DashboardRendererProps) {
  const getTrendColor = () => {
    switch (trend) {
      case "up":
        return "text-green-600";
      case "down":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  const getTrendIcon = () => {
    switch (trend) {
      case "up":
        return "↑";
      case "down":
        return "↓";
      default:
        return "→";
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <h3 className="text-lg font-semibold text-gray-800 capitalize">
          {metric} Analysis
        </h3>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-4 p-4">
        <div className="text-center">
          <div className="text-sm text-gray-500">Current</div>
          <div className="text-2xl font-bold text-gray-800">
            {formatNumber(current)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-500">Previous</div>
          <div className="text-2xl font-bold text-gray-600">
            {formatNumber(previous)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-500">Change</div>
          <div className={`text-2xl font-bold ${getTrendColor()}`}>
            {getTrendIcon()} {Math.abs(change)}%
          </div>
        </div>
      </div>

      {/* Chart */}
      {chart && chart.data && (
        <div className="px-4 pb-4">
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chart.data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 12 }}
                  stroke="#888"
                />
                <YAxis tick={{ fontSize: 12 }} stroke="#888" />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={trend === "up" ? "#22c55e" : trend === "down" ? "#ef4444" : "#6b7280"}
                  strokeWidth={2}
                  dot={{ fill: "#fff", stroke: "#8884d8", strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Insights */}
      {insights.length > 0 && (
        <div className="px-4 pb-4">
          <div className="bg-gray-50 rounded-lg p-3">
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Key Insights
            </h4>
            <ul className="space-y-1">
              {insights.map((insight, index) => (
                <li
                  key={index}
                  className="text-sm text-gray-600 flex items-start gap-2"
                >
                  <span className="text-blue-500">•</span>
                  {insight}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
