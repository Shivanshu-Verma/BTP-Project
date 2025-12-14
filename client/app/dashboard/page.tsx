"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { protectedFetch } from "@/lib/protectedFetch";
import { logout } from "@/lib/auth";
import { toast, ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

import UploadReceipt from "@/components/UploadReceipt";
import ReceiptsList from "@/components/ReceiptsList";
import SpendingCharts from "@/components/SpendingCharts";
import AIQuery from "@/components/AIQuery";
import { Receipt } from "@/types/receipt";

export default function Dashboard() {
  const router = useRouter();
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loading, setLoading] = useState(true);

  // Auth check + initial fetch
  useEffect(() => {
    const fetchReceipts = async () => {
      try {
        const res = await protectedFetch("/receipts/");
        
        if (!res.ok) {
          if (res.status === 401) {
            toast.error("Session expired. Please login again.");
            router.push("/auth");
            return;
          }
          throw new Error("Failed to fetch receipts");
        }
        
        const data = await res.json();
        setReceipts(Array.isArray(data) ? data : []);
      } catch (error) {
        console.error("Error fetching receipts:", error);
        toast.error("Failed to load receipts. Please try again.");
        setReceipts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchReceipts();
  }, [router]);

  async function handleLogout() {
    try {
      await logout();
      toast.success("Logged out successfully");
      setTimeout(() => {
        router.push("/auth");
      }, 500);
    } catch (error) {
      console.error("Logout error:", error);
      toast.error("Logout failed. Please try again.");
    }
  }

  function handleNewReceipt(receipt: Receipt) {
    if (receipt && receipt.id) {
      setReceipts(prev => [receipt, ...prev]);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop={true}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="dark"
      />

      <div className="max-w-7xl mx-auto p-6 space-y-6">
        <header className="flex justify-between items-center bg-gray-800/50 backdrop-blur-xl rounded-2xl border border-gray-700/50 p-6 shadow-xl">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Dashboard
            </h1>
            <p className="text-gray-400 text-sm mt-1">Manage your receipts and expenses</p>
          </div>
          <button
            onClick={handleLogout}
            className="bg-gradient-to-r from-red-500 to-red-600 text-white px-6 py-2.5 rounded-lg hover:from-red-600 hover:to-red-700 transition duration-200 transform hover:scale-105 font-semibold shadow-lg shadow-red-500/30"
          >
            Logout
          </button>
        </header>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <svg
                className="animate-spin h-12 w-12 text-blue-500 mx-auto mb-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              <p className="text-gray-400">Loading dashboard...</p>
            </div>
          </div>
        ) : (
          <>
            <AIQuery />
            <UploadReceipt onUploaded={handleNewReceipt} />
            <SpendingCharts />
            <ReceiptsList receipts={receipts} setReceipts={setReceipts} />
          </>
        )}
      </div>
    </div>
  );
}