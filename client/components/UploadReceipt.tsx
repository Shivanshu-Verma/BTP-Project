"use client";

import { useState } from "react";
import { toast } from "react-toastify";
import { protectedFetch } from "@/lib/protectedFetch";
import { ReceiptStatus, Receipt } from "@/types/receipt";

type UploadInitResponse = {
  uploads: {
    receipt_id: number;
    object_name: string;
    upload_url: string;
    status: string;
  }[];
};

export default function UploadReceipt({
  onUploaded,
}: {
  onUploaded: (r: Receipt) => void;
}) {
  const [uploading, setUploading] = useState(false);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    // ---- validations ----
    const validTypes = [".jpg", ".jpeg", ".png", ".heic", ".pdf"];
    const invalid = files.filter((f) => {
      const ext = "." + f.name.split(".").pop()?.toLowerCase();
      return !validTypes.includes(ext);
    });

    if (invalid.length > 0) {
      toast.error("Invalid file type. Upload images or PDFs only.");
      e.target.value = "";
      return;
    }

    const oversized = files.filter((f) => f.size > 10 * 1024 * 1024);
    if (oversized.length > 0) {
      toast.error("Each file must be under 10MB.");
      e.target.value = "";
      return;
    }

    setUploading(true);

    try {
      // =============================
      // 1️⃣ INIT UPLOAD (BACKEND)
      // =============================
      const initRes = await protectedFetch("/receipts/upload/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          files: files.map((f) => ({
            filename: f.name,
            content_type: f.type,
          })),
        }),
      });

      if (!initRes.ok) {
        throw new Error("Upload initialization failed");
      }

      const data: UploadInitResponse = await initRes.json();

      if (!Array.isArray(data.uploads)) {
        throw new Error("Invalid init response");
      }

      // =============================
      // 2️⃣ UPLOAD FILES TO GCS
      // =============================
      const uploadedReceiptIds: number[] = [];

      for (let i = 0; i < data.uploads.length; i++) {
        const upload = data.uploads[i];
        const file = files[i];

        const res = await fetch(upload.upload_url, {
          method: "PUT",
          headers: {
            "Content-Type": file.type,
          },
          body: file,
        });

        if (!res.ok) {
          throw new Error(`Failed to upload ${file.name}`);
        }

        uploadedReceiptIds.push(upload.receipt_id);
      }

      // =============================
      // 3️⃣ CONFIRM UPLOAD (BACKEND)
      // =============================
      const completeRes = await protectedFetch("/receipts/complete/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          receipt_ids: uploadedReceiptIds,
        }),
      });

      if (!completeRes.ok) {
        throw new Error("Failed to confirm upload");
      }

      // =============================
      // 4️⃣ UPDATE UI
      // =============================
      uploadedReceiptIds.forEach((id) => {
        onUploaded({
          id,
          status: data.uploads.find((u) => u.receipt_id === id)?.status as ReceiptStatus,
        });
      });

      toast.success(
        `${uploadedReceiptIds.length} receipt${
          uploadedReceiptIds.length > 1 ? "s" : ""
        } uploaded successfully`
      );
    } catch (err) {
      console.error(err);
      toast.error("Receipt upload failed. Please try again.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <section className="bg-gray-800/50 border border-gray-700/50 p-6 rounded-2xl shadow-lg">
      <h2 className="text-xl font-semibold text-white mb-2">
        Upload Receipts
      </h2>
      <p className="text-gray-400 text-sm mb-4">
        Upload images or PDFs (max 10MB per file)
      </p>

      <input
        type="file"
        multiple
        accept=".jpg,.jpeg,.png,.heic,.pdf"
        onChange={handleUpload}
        disabled={uploading}
        className="block w-full text-sm text-gray-400
          file:mr-4 file:py-2 file:px-4
          file:rounded-lg file:border-0
          file:text-sm file:font-semibold
          file:bg-blue-600 file:text-white
          hover:file:bg-blue-700
          disabled:opacity-50"
      />

      {uploading && (
        <p className="text-blue-400 text-sm mt-3">
          Uploading receipts…
        </p>
      )}
    </section>
  );
}
