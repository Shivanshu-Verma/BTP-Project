"use client";

import { useEffect } from "react";
import { protectedFetch } from "@/lib/protectedFetch";
import { logout } from "@/lib/auth";
import { useRouter } from "next/navigation";

export default function Dashboard() {
  const router = useRouter();

  useEffect(() => {
    protectedFetch("/api/receipts/")
      .then((res) => {
        if (!res.ok) throw new Error();
      })
      .catch(() => router.push("/auth"));
  }, []);

  async function handleLogout() {
    await logout();
    router.push("/auth");
  }

  return (
    <div>
      <h1>Dashboard</h1>
      <button onClick={handleLogout}>Logout</button>
    </div>
  );
}
