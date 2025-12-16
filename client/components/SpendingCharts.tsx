"use client";

import { useEffect, useMemo, useState } from "react";
import { Bar } from "react-chartjs-2";
import { protectedFetch } from "@/lib/protectedFetch";
import { toast } from "react-toastify";
import "@/lib/chart";

/* ---------------- TYPES ---------------- */

type Receipt = {
  id: number;
  merchant_name: string | null;
  total_amount: string | null;
  purchase_date: string | null;
  created_at: string;
  status: string;
};

type DailySpend = { date: string; amount: number };
type MonthlySpend = { month: string; amount: number };

/* ---------------- HELPERS ---------------- */

const formatINR = (value: number) =>
  `₹${value.toLocaleString("en-IN")}`;

const getMonthKey = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;

const getDateKey = (date: Date) =>
  date.toISOString().split("T")[0];

/* ---------------- COMPONENT ---------------- */

export default function SpendingCharts() {
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [daily, setDaily] = useState<DailySpend[]>([]);
  const [monthly, setMonthly] = useState<MonthlySpend[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  /* ---------------- FETCH ---------------- */

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await protectedFetch("/receipts/analytics/");
        if (!res.ok) throw new Error("Fetch failed");

        const data: Receipt[] = await res.json();
        setReceipts(data);
      } catch {
        toast.error("Failed to load analytics");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  /* ---------------- PROCESS DATA ---------------- */

  useEffect(() => {
    if (!receipts.length) return;

    const now = new Date();
    const currentMonthKey = getMonthKey(now);

    /* ---- DAY-WISE (CURRENT MONTH) ---- */

    const daysInMonth = new Date(
      now.getFullYear(),
      now.getMonth() + 1,
      0
    ).getDate();

    const dayMap = new Map<string, number>();

    for (let d = 1; d <= daysInMonth; d++) {
      const date = new Date(now.getFullYear(), now.getMonth(), d);
      dayMap.set(getDateKey(date), 0);
    }

    receipts.forEach(r => {
      if (
        r.status !== "READY" ||
        !r.total_amount ||
        !r.purchase_date
      )
        return;

      const date = new Date(r.purchase_date);
      if (getMonthKey(date) !== currentMonthKey) return;

      const key = getDateKey(date);
      dayMap.set(
        key,
        dayMap.get(key)! + Number(r.total_amount)
      );
    });

    setDaily(
      Array.from(dayMap.entries()).map(([date, amount]) => ({
        date,
        amount,
      }))
    );

    /* ---- MONTH-WISE (LAST 12 MONTHS) ---- */

    const monthMap = new Map<string, number>();

    for (let i = 11; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      monthMap.set(getMonthKey(d), 0);
    }

    receipts.forEach(r => {
      if (
        r.status !== "READY" ||
        !r.total_amount ||
        !r.purchase_date
      )
        return;

      const date = new Date(r.purchase_date);
      const key = getMonthKey(date);

      if (monthMap.has(key)) {
        monthMap.set(
          key,
          monthMap.get(key)! + Number(r.total_amount)
        );
      }
    });

    setMonthly(
      Array.from(monthMap.entries()).map(([month, amount]) => ({
        month,
        amount,
      }))
    );
  }, [receipts]);

  /* ---------------- TOOLTIP MERCHANT BREAKDOWN ---------------- */

  const merchantBreakdown = useMemo(() => {
    if (!selectedDate) return [];

    return receipts.filter(
      r =>
        r.status === "READY" &&
        r.total_amount &&
        r.purchase_date &&
        getDateKey(new Date(r.purchase_date)) === selectedDate
    );
  }, [selectedDate, receipts]);

  /* ---------------- RENDER ---------------- */

  if (loading) {
    return <div className="p-6 text-gray-400">Loading analytics…</div>;
  }

  return (
    <section className="space-y-10">
      {/* ---------------- DAY-WISE ---------------- */}
      <div className="bg-gray-900/30 p-5 rounded-xl">
        <h3 className="text-white mb-4">
          Day-wise Spending (Current Month)
        </h3>

        <Bar
          data={{
            labels: daily.map(d => d.date),
            datasets: [
              {
                label: "Daily Spend",
                data: daily.map(d => d.amount),
                backgroundColor: "rgba(59,130,246,0.8)",
              },
            ],
          }}
          options={{
            responsive: true,
            onClick: (_, elements) => {
              if (!elements.length) return;
              const index = elements[0].index;
              setSelectedDate(daily[index].date);
            },
            plugins: {
              tooltip: {
                callbacks: {
                  label: ctx =>
                    formatINR(ctx.parsed.y),
                },
              },
            },
            scales: {
              y: {
                beginAtZero: true,
                ticks: {
                  callback: value => formatINR(Number(value)),
                },
              },
            },
          }}
        />
      </div>

      {/* ---------------- CLICKED DAY RECEIPTS ---------------- */}
      {selectedDate && (
        <div className="bg-gray-900/30 p-5 rounded-xl">
          <h4 className="text-white mb-3">
            Receipts on {selectedDate}
          </h4>

          {merchantBreakdown.length === 0 ? (
            <p className="text-gray-400">No spending</p>
          ) : (
            <ul className="space-y-2">
              {merchantBreakdown.map(r => (
                <li
                  key={r.id}
                  className="flex justify-between text-gray-300"
                >
                  <span>{r.merchant_name ?? "Unknown"}</span>
                  <span>{formatINR(Number(r.total_amount))}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* ---------------- MONTH-WISE ---------------- */}
      <div className="bg-gray-900/30 p-5 rounded-xl">
        <h3 className="text-white mb-4">Month-wise Spending</h3>

        <Bar
          data={{
            labels: monthly.map(m => m.month),
            datasets: [
              {
                label: "Monthly Spend",
                data: monthly.map(m => m.amount),
                backgroundColor: "rgba(168,85,247,0.85)",
              },
            ],
          }}
          options={{
            responsive: true,
            scales: {
              y: {
                beginAtZero: true,
                ticks: {
                  callback: value => formatINR(Number(value)),
                },
              },
            },
            plugins: {
              tooltip: {
                callbacks: {
                  label: ctx =>
                    formatINR(ctx.parsed.y),
                },
              },
            },
          }}
        />
      </div>
    </section>
  );
}