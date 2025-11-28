"use client";

interface Action {
  label: string;
  action: string;
  primary?: boolean;
}

interface CardRendererProps {
  title?: string;
  content?: string;
  imageUrl?: string;
  price?: string;
  inStock?: boolean;
  category?: string;
  actions?: Action[];
}

export function CardRenderer({
  title = "Card",
  content = "",
  imageUrl,
  price,
  inStock,
  category,
  actions = [],
}: CardRendererProps) {
  const handleAction = (action: string) => {
    // In a real app, this would trigger actual actions
    console.log("Action triggered:", action);
    alert(`Action: ${action}\nIn a real app, this would trigger the "${action}" action.`);
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden max-w-sm">
      {imageUrl && (
        <div className="relative">
          <img
            src={imageUrl}
            alt={title}
            className="w-full h-48 object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).src =
                "https://placehold.co/400x200/png?text=Image+Not+Found";
            }}
          />
          {category && (
            <span className="absolute top-2 left-2 bg-blue-600 text-white text-xs px-2 py-1 rounded">
              {category}
            </span>
          )}
          {inStock !== undefined && (
            <span
              className={`absolute top-2 right-2 text-xs px-2 py-1 rounded ${
                inStock
                  ? "bg-green-100 text-green-800"
                  : "bg-red-100 text-red-800"
              }`}
            >
              {inStock ? "In Stock" : "Out of Stock"}
            </span>
          )}
        </div>
      )}

      <div className="p-4">
        <h3 className="text-xl font-semibold text-gray-800">{title}</h3>

        {content && (
          <p className="mt-2 text-gray-600 text-sm leading-relaxed">
            {content}
          </p>
        )}

        {price && (
          <p className="mt-4 text-2xl font-bold text-gray-900">{price}</p>
        )}

        {actions.length > 0 && (
          <div className="mt-4 flex gap-2 flex-wrap">
            {actions.map((action, index) => (
              <button
                key={index}
                onClick={() => handleAction(action.action)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  action.primary
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
