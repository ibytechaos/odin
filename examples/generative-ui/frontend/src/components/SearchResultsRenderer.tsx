"use client";

import { CardRenderer } from "./CardRenderer";

interface SearchResultsRendererProps {
  query?: string;
  total?: number;
  results?: Array<{
    component: string;
    title: string;
    content: string;
    imageUrl?: string;
    price?: string;
    category?: string;
    actions?: Array<{ label: string; action: string; primary?: boolean }>;
  }>;
}

export function SearchResultsRenderer({
  query = "",
  total = 0,
  results = [],
}: SearchResultsRendererProps) {
  if (!results || results.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-8 text-center">
        <div className="text-4xl mb-4">🔍</div>
        <h3 className="text-lg font-semibold text-gray-800">No results found</h3>
        <p className="text-gray-500 mt-2">
          No products found for "{query}". Try a different search term.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-800">
              Search Results
            </h3>
            <p className="text-sm text-gray-500">
              Found {total} result{total !== 1 ? "s" : ""} for "{query}"
            </p>
          </div>
        </div>
      </div>

      {/* Results grid */}
      <div className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {results.map((result, index) => (
            <CardRenderer
              key={index}
              title={result.title}
              content={result.content}
              imageUrl={result.imageUrl}
              price={result.price}
              category={result.category}
              actions={result.actions}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
