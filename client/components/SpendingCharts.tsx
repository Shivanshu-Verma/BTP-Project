"use client";

import { useEffect, useState } from "react";
import { Line, Bar } from "react-chartjs-2";
import { protectedFetch } from "@/lib/protectedFetch";
import { toast } from "react-toastify";

type Analytics = {
  daily: { date: string; amount: number }[];
  monthly: { month: string; amount: number }[];
};

export default function SpendingCharts() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await protectedFetch("/receipts/analytics/");
        
        if (!res.ok) {
          throw new Error("Failed to fetch analytics");
        }
        
        const responseData = await res.json();
        
        setData({
          daily: Array.isArray(responseData?.daily) ? responseData.daily : [],
          monthly: Array.isArray(responseData?.monthly) ? responseData.monthly : [],
        });
      } catch (error) {
        console.error("Analytics error:", error);
        toast.error("Failed to load spending analytics");
        setData({ daily: [], monthly: [] });
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <section className="bg-gray-800/50 backdrop-blur-xl border border-gray-700/50 p-6 rounded-2xl shadow-xl">
        <div className="flex items-center justify-center py-12">
          <svg
            className="animate-spin h-8 w-8 text-blue-500 mr-3"
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
          <p className="text-gray-400">Loading analytics...</p>
        </div>
      </section>
    );
  }

  if (!data || (data.daily.length === 0 && data.monthly.length === 0)) {
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
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <p className="text-gray-400 text-lg">No spending data yet</p>
          <p className="text-gray-500 text-sm mt-2">
            Upload receipts to see your spending analytics
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="bg-gray-800/50 backdrop-blur-xl border border-gray-700/50 p-6 rounded-2xl shadow-xl space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Spending Analytics</h2>
        <svg
          className="w-8 h-8 text-purple-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
      </div>

      {data.daily.length > 0 && (
        <div className="bg-gray-900/30 p-5 rounded-xl border border-gray-700/30">
          <h3 className="text-lg font-semibold text-white mb-4">Last 30 Days</h3>
          <Line
            data={{
              labels: data.daily.map(d => d.date),
              datasets: [
                {
                  label: "Daily Spend",
                  data: data.daily.map(d => d.amount),
                  borderColor: "rgb(59, 130, 246)",
                  backgroundColor: "rgba(59, 130, 246, 0.1)",
                  tension: 0.4,
                },
              ],
            }}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  labels: { color: "#9CA3AF" },
                },
              },
              scales: {
                x: {
                  ticks: { color: "#9CA3AF" },
                  grid: { color: "rgba(156, 163, 175, 0.1)" },
                },
                y: {
                  ticks: { color: "#9CA3AF" },
                  grid: { color: "rgba(156, 163, 175, 0.1)" },
                },
              },
            }}
          />
        </div>
      )}

      {data.monthly.length > 0 && (
        <div className="bg-gray-900/30 p-5 rounded-xl border border-gray-700/30">
          <h3 className="text-lg font-semibold text-white mb-4">Last 12 Months</h3>
          <Bar
            data={{
              labels: data.monthly.map(m => m.month),
              datasets: [
                {
                  label: "Monthly Spend",
                  data: data.monthly.map(m => m.amount),
                  backgroundColor: "rgba(168, 85, 247, 0.8)",
                  borderColor: "rgb(168, 85, 247)",
                  borderWidth: 1,
                },
              ],
            }}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  labels: { color: "#9CA3AF" },
                },
              },
              scales: {
                x: {
                  ticks: { color: "#9CA3AF" },
                  grid: { color: "rgba(156, 163, 175, 0.1)" },
                },
                y: {
                  ticks: { color: "#9CA3AF" },
                  grid: { color: "rgba(156, 163, 175, 0.1)" },
                },
              },
            }}
          />
        </div>
      )}
    </section>
  );
}