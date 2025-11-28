"use client";

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface ChartRendererProps {
  chartType?: string;
  title?: string;
  data?: Array<{ name: string; value: number }>;
  xAxis?: string;
  yAxis?: string;
  summary?: {
    total?: number;
    average?: number;
    period?: string;
  };
}

const COLORS = ["#8884d8", "#82ca9d", "#ffc658", "#ff7300", "#0088fe"];

export function ChartRenderer({
  chartType = "bar",
  title = "Chart",
  data = [],
  xAxis = "name",
  yAxis = "value",
  summary,
}: ChartRendererProps) {
  if (!data || data.length === 0) {
    return (
      <div className="p-4 bg-gray-100 rounded-lg text-center text-gray-500">
        No data available
      </div>
    );
  }

  const renderChart = () => {
    switch (chartType) {
      case "line":
        return (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xAxis} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey={yAxis}
              stroke="#8884d8"
              strokeWidth={2}
              dot={{ fill: "#8884d8" }}
            />
          </LineChart>
        );
      case "pie":
        return (
          <PieChart>
            <Pie
              data={data}
              dataKey={yAxis}
              nameKey={xAxis}
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={({ name, percent }) =>
                `${name}: ${(percent * 100).toFixed(0)}%`
              }
            >
              {data.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        );
      default: // bar
        return (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xAxis} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey={yAxis} fill="#8884d8" radius={[4, 4, 0, 0]} />
          </BarChart>
        );
    }
  };

  return (
    <div className="p-4 bg-white rounded-lg shadow-md border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">{title}</h3>

      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          {renderChart()}
        </ResponsiveContainer>
      </div>

      {summary && (
        <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-3 gap-4 text-center">
          {summary.total !== undefined && (
            <div>
              <div className="text-sm text-gray-500">Total</div>
              <div className="text-lg font-semibold text-gray-800">
                {summary.total.toLocaleString()}
              </div>
            </div>
          )}
          {summary.average !== undefined && (
            <div>
              <div className="text-sm text-gray-500">Average</div>
              <div className="text-lg font-semibold text-gray-800">
                {summary.average.toLocaleString()}
              </div>
            </div>
          )}
          {summary.period && (
            <div>
              <div className="text-sm text-gray-500">Period</div>
              <div className="text-lg font-semibold text-gray-800 capitalize">
                {summary.period}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
