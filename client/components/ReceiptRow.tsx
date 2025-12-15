import { Receipt } from "@/types/receipt";
import { protectedFetch } from "@/lib/protectedFetch";
import { toast } from "react-toastify";

export default function ReceiptRow({ receipt }: { receipt: Receipt }) {
  if (!receipt || !receipt.id) {
    return null;
  }

  async function handleView() {
    try {
      const res = await protectedFetch(`/receipts/${receipt.id}/view-url/`);

      if (!res.ok) {
        if (res.status === 404) {
          toast.info("Receipt file not available yet");
          return;
        }
        throw new Error("Failed to fetch receipt URL");
      }

      const data = await res.json();

      if (!data?.view_url) {
        toast.info("Receipt file is not ready yet");
        return;
      }

      window.open(data.view_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      console.error("View receipt error:", err);
      toast.error("Unable to view receipt. Please try again later.");
    }
  }

  return (
    <div className="flex justify-between items-center p-4 bg-gray-900/30 border border-gray-700/50 rounded-xl hover:border-gray-600/50 transition duration-200">
      <div className="flex items-center space-x-3">
        <div
          className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            receipt.status === "READY"
              ? "bg-gradient-to-br from-green-500 to-green-600"
              : "bg-gray-700"
          }`}
        >
          {receipt.status === "READY" ? (
            <svg
              className="w-6 h-6 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
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
          )}
        </div>

        <div>
          <span className="text-white font-medium block">
            {receipt.merchant_name || `Receipt #${receipt.id}`}
          </span>
          <span className="text-gray-500 text-xs">
            Status: {receipt.status}
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <span className="text-green-400 font-semibold text-lg">
          ₹{Number(receipt.total_amount || 0).toFixed(2)}
        </span>

        {/* 👁 View button ALWAYS visible */}
        <button
          onClick={handleView}
          className="px-4 py-2 text-sm font-semibold rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 transition"
        >
          View
        </button>

        <StatusBadge status={receipt.status} />
      </div>
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