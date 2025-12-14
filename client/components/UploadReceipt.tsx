"use client";

import { protectedFetch } from "@/lib/protectedFetch";
import { Receipt } from "@/types/receipt";
import { toast } from "react-toastify";
import { useState } from "react";

type UploadInitResponse = {
  uploads: {
    receipt_id: number;
    presigned_url: string;
    file_key: string;
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

    // Validate file types
    const validTypes = [".jpg", ".jpeg", ".png", ".heic", ".pdf"];
    const invalidFiles = files.filter(f => {
      const ext = "." + f.name.split(".").pop()?.toLowerCase();
      return !validTypes.includes(ext);
    });

    if (invalidFiles.length > 0) {
      toast.error("Invalid file type. Please upload images or PDFs only.");
      e.target.value = "";
      return;
    }

    // Validate file sizes (10MB limit)
    const oversizedFiles = files.filter(f => f.size > 10 * 1024 * 1024);
    if (oversizedFiles.length > 0) {
      toast.error("File size exceeds 10MB limit.");
      e.target.value = "";
      return;
    }

    setUploading(true);

    try {
      // 1️⃣ Init upload
      const initRes = await protectedFetch("/receipts/upload/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          files: files.map(f => ({
            filename: f.name,
            content_type: f.type,
          })),
        }),
      });

      if (!initRes.ok) {
        throw new Error("Failed to initialize upload");
      }

      const data: UploadInitResponse = await initRes.json();

      if (!data.uploads || !Array.isArray(data.uploads)) {
        throw new Error("Invalid response format");
      }

      // 2️⃣ Upload each file directly to S3
      const uploadPromises = data.uploads.map(async (u, index) => {
        try {
          const uploadRes = await fetch(u.presigned_url, {
            method: "PUT",
            headers: { "Content-Type": files[index].type },
            body: files[index],
          });

          if (!uploadRes.ok) {
            throw new Error(`Failed to upload ${files[index].name}`);
          }

          return { success: true, upload: u };
        } catch (error) {
          console.error(`Upload error for ${files[index].name}:`, error);
          return { success: false, upload: u };
        }
      });

      const results = await Promise.all(uploadPromises);
      const successfulUploads = results.filter(r => r.success);
      const failedUploads = results.filter(r => !r.success);

      // 3️⃣ Push successful receipts into UI immediately
      successfulUploads.forEach(({ upload }) => {
        onUploaded({
          id: upload.receipt_id,
          status: upload.status as any,
        });
      });

      if (successfulUploads.length > 0) {
        toast.success(
          `${successfulUploads.length} receipt${successfulUploads.length > 1 ? "s" : ""} uploaded successfully!`
        );
      }

      if (failedUploads.length > 0) {
        toast.error(
          `${failedUploads.length} receipt${failedUploads.length > 1 ? "s" : ""} failed to upload.`
        );
      }
    } catch (error) {
      console.error("Upload error:", error);
      toast.error("Failed to upload receipts. Please try again.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <section className="bg-gray-800/50 backdrop-blur-xl border border-gray-700/50 p-6 rounded-2xl shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold text-white">Upload Receipts</h2>
          <p className="text-gray-400 text-sm mt-1">
            Upload your receipts for automatic processing
          </p>
        </div>
        <svg
          className="w-8 h-8 text-blue-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
      </div>

      <label className="block">
        <input
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.heic,.pdf"
          onChange={handleUpload}
          disabled={uploading}
          className="block w-full text-sm text-gray-400
            file:mr-4 file:py-2.5 file:px-4
            file:rounded-lg file:border-0
            file:text-sm file:font-semibold
            file:bg-gradient-to-r file:from-blue-500 file:to-purple-600
            file:text-white
            hover:file:from-blue-600 hover:file:to-purple-700
            file:transition file:duration-200
            file:cursor-pointer
            file:shadow-lg file:shadow-blue-500/30
            disabled:opacity-50 disabled:cursor-not-allowed"
        />
      </label>

      {uploading && (
        <div className="mt-4 flex items-center text-blue-400">
          <svg
            className="animate-spin h-5 w-5 mr-2"
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
          <span className="text-sm">Uploading receipts...</span>
        </div>
      )}

      <p className="text-xs text-gray-500 mt-3">
        Supported formats: JPG, JPEG, PNG, HEIC, PDF (Max 10MB per file)
      </p>
    </section>
  );
}