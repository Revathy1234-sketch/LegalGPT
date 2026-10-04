"use client";

import { AppShell } from "@/src/components/layout/app-shell";
import { UploadCloud, File, X, ChevronRight, Loader2 } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { contractsApi } from "@/src/lib/api/contracts";

export default function UploadContract() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => contractsApi.upload(file),
    onSuccess: (data) => {
      router.push(`/contracts/${data.id}`);
    },
    onError: (error: { response?: { data?: { detail?: string } } } | Error | unknown) => {
      const err = error as { response?: { data?: { detail?: string } } };
      setServerError(err.response?.data?.detail || "An error occurred during upload.");
    }
  });

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === "application/pdf") {
        setFile(droppedFile);
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type === "application/pdf") {
        setFile(selectedFile);
      }
    }
  };

  const handleUpload = () => {
    if (!file) return;
    setServerError(null);
    uploadMutation.mutate(file);
  };

  return (
    <AppShell>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Upload Contract</h1>
          <p className="text-slate-700/60 mt-1 font-medium">Add a new document to your workspace for analysis.</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm p-6 sm:p-10">
        <div className="flex items-center justify-center mb-10">
          <div className="flex items-center text-sm font-medium">
            <div className="flex items-center text-blue-600">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-blue-600 bg-white shadow-sm">1</span>
              <span className="ml-3 hidden sm:block">Upload</span>
            </div>
            <ChevronRight className="h-5 w-5 text-slate-300 mx-3 sm:mx-4" />
            <div className="flex items-center text-slate-700/40">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-slate-200/80 bg-white">2</span>
              <span className="ml-3 hidden sm:block">Process</span>
            </div>
            <ChevronRight className="h-5 w-5 text-slate-300 mx-3 sm:mx-4" />
            <div className="flex items-center text-slate-700/40">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-slate-200/80 bg-white">3</span>
              <span className="ml-3 hidden sm:block">Analyze</span>
            </div>
            <ChevronRight className="h-5 w-5 text-slate-300 mx-3 sm:mx-4" />
            <div className="flex items-center text-slate-700/40">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-slate-200/80 bg-white">4</span>
              <span className="ml-3 hidden sm:block">Review</span>
            </div>
          </div>
        </div>

        <div className="max-w-2xl mx-auto">
          {!file ? (
            <div
              className={`mt-2 flex justify-center rounded-xl border-2 border-dashed px-6 py-16 transition-all ${
                isDragging ? "border-blue-500 bg-blue-50" : "border-slate-200/80 bg-slate-50 hover:bg-slate-100 hover:border-slate-400"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 mb-4 shadow-sm border border-blue-200">
                  <UploadCloud className="h-8 w-8 text-blue-600" />
                </div>
                <div className="mt-4 flex text-sm leading-6 text-slate-700/80 justify-center items-center">
                  <label
                    htmlFor="file-upload"
                    className="relative cursor-pointer rounded-md bg-transparent font-semibold text-blue-600 focus-within:outline-none focus-within:ring-2 focus-within:ring-blue-600 focus-within:ring-offset-2 hover:text-blue-600/90 transition-colors"
                  >
                    <span>Select a PDF</span>
                    <input id="file-upload" name="file-upload" type="file" className="sr-only" accept="application/pdf" onChange={handleFileChange} />
                  </label>
                  <p className="pl-1">or drag and drop</p>
                </div>
                <p className="text-xs leading-5 text-slate-700/60 mt-2 font-medium">Only PDF files are supported currently</p>
              </div>
            </div>
          ) : (
            <div className="mt-2 rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-blue-50 text-blue-600 rounded-lg shrink-0 border border-blue-100">
                  <File className="h-8 w-8" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-semibold text-slate-900 truncate">{file.name}</h4>
                  <p className="text-sm text-slate-700/60 mt-1 font-medium">{(file.size / 1024 / 1024).toFixed(2)} MB</p>

                  {uploadMutation.isPending && (
                    <div className="mt-5">
                      <div className="flex items-center justify-between text-sm font-medium text-slate-900 mb-2">
                        <span>Uploading and parsing...</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                        <div className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out shadow-sm w-full animate-pulse"></div>
                      </div>
                    </div>
                  )}
                </div>
                {!uploadMutation.isPending && (
                  <button
                    onClick={() => {
                      setFile(null);
                      setServerError(null);
                    }}
                    className="p-2 text-slate-700/40 hover:text-rose-600 hover:bg-rose-50 rounded-full transition-colors outline-none focus:ring-2 focus:ring-rose-500"
                    aria-label="Remove file"
                  >
                    <X className="h-5 w-5" />
                  </button>
                )}
              </div>

              {serverError && (
                <div className="mt-4 p-3 text-sm text-rose-600 bg-rose-50 rounded-md border border-rose-100">
                  {serverError}
                </div>
              )}

              <div className="mt-8 flex gap-3 justify-end border-t border-slate-100 pt-6">
                <button
                  onClick={() => {
                    setFile(null);
                    setServerError(null);
                  }}
                  disabled={uploadMutation.isPending}
                  className="px-4 py-2 border border-slate-200/80 text-slate-700 rounded-lg hover:bg-slate-50 font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed outline-none focus:ring-2 focus:ring-slate-300"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  disabled={uploadMutation.isPending}
                  className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-600/90 font-medium text-sm transition-colors shadow-sm disabled:opacity-75 disabled:cursor-wait flex items-center gap-2 outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
                >
                  {uploadMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    "Upload and Analyze"
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
