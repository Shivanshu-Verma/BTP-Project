"use client";

import { Receipt } from "@/types/receipt";
import ReceiptRow from "./ReceiptRow";

export default function ReceiptsList({
  receipts,
  setReceipts,
}: {
  receipts: Receipt[];
  setReceipts: (r: Receipt[]) => void;
}) {
  const safeReceipts = Array.isArray(receipts) ? receipts : [];

  if (safeReceipts.length === 0) {
    return (
      <section className="bg-gray-800/50 backdrop-blur-xl border border-gray-700/50 p-6 rounded-2xl shadow-xl">
        <div className="text-center py-12">
          <svg
            className="w-16 h-16 text-gray-600 mx-auto mb-4"
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
          <p className="text-gray-400 text-lg">No receipts yet</p>
          <p className="text-gray-500 text-sm mt-2">
            Upload your first receipt to get started
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="bg-gray-800/50 backdrop-blur-xl border border-gray-700/50 p-6 rounded-2xl shadow-xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white">Your Receipts</h2>
          <p className="text-gray-400 text-sm mt-1">
            {safeReceipts.length} receipt{safeReceipts.length !== 1 ? "s" : ""} total
          </p>
        </div>
        <svg
          className="w-8 h-8 text-green-400"
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

      <div className="space-y-3">
        {safeReceipts.map(receipt => (
          <ReceiptRow key={receipt.id} receipt={receipt} />
        ))}
      </div>
    </section>
  );
}