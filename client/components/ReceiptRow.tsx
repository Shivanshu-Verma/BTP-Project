import { Receipt } from "@/types/receipt";

export default function ReceiptRow({ receipt }: { receipt: Receipt }) {
  if (!receipt || !receipt.id) {
    return null;
  }

  if (receipt.status !== "READY") {
    return (
      <div className="flex justify-between items-center p-4 bg-gray-900/30 border border-gray-700/50 rounded-xl hover:border-gray-600/50 transition duration-200">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gray-700 rounded-lg flex items-center justify-center">
            <svg
              className="w-6 h-6 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <span className="text-gray-300 font-medium">Receipt #{receipt.id}</span>
        </div>
        <StatusBadge status={receipt.status} />
      </div>
    );
  }

  return (
    <div className="flex justify-between items-center p-4 bg-gray-900/30 border border-gray-700/50 rounded-xl hover:border-gray-600/50 transition duration-200">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
          <svg
            className="w-6 h-6 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <div>
          <span className="text-white font-medium block">
            {receipt.merchant_name || "Unknown Merchant"}
          </span>
          <span className="text-gray-500 text-xs">Receipt #{receipt.id}</span>
        </div>
      </div>
      <span className="text-green-400 font-semibold text-lg">
        ₹{Number(receipt.total_amount || 0).toFixed(2)}
      </span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { label: string; color: string; bgColor: string }> = {
    PENDING: { label: "Uploaded", color: "text-blue-400", bgColor: "bg-blue-500/20" },
    PROCESSING: { label: "Processing", color: "text-yellow-400", bgColor: "bg-yellow-500/20" },
    READY: { label: "Ready", color: "text-green-400", bgColor: "bg-green-500/20" },
    FAILED: { label: "Failed", color: "text-red-400", bgColor: "bg-red-500/20" },
  };

  const config = statusConfig[status] || statusConfig.PENDING;

  return (
    <span
      className={`${config.color} ${config.bgColor} px-3 py-1 rounded-full text-sm font-semibold border border-current/20`}
    >
      {config.label}
    </span>
  );
}