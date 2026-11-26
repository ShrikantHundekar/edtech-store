import React, { useState, useRef } from 'react';
import {
  X,
  UploadCloud,
  FileText,
  AlertCircle,
  Trash2,
  Loader2,
} from 'lucide-react';
import { adminCatalogService } from '../../services/adminCatalogService';
import type { Chapter } from '../../types/catalog';

interface PDFUploadModalProps {
  chapter: Chapter;
  onClose: () => void;
  onSuccess: (material: any) => void;
}

export const PDFUploadModal: React.FC<PDFUploadModalProps> = ({
  chapter,
  onClose,
  onSuccess,
}) => {
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState<string>('');
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Client-side validation function (Rejects non-PDF files before network request)
  const validateAndSetFile = (file: File) => {
    setErrorMessage(null);

    // 1. Validate PDF extension and MIME type
    const isPdfMime = file.type === 'application/pdf';
    const isPdfExt = file.name.toLowerCase().endsWith('.pdf');

    if (!isPdfMime && !isPdfExt) {
      setErrorMessage(
        `Invalid file type "${file.name}". Only PDF documents (.pdf) are permitted.`
      );
      setSelectedFile(null);
      return;
    }

    // 2. Validate max size (25MB)
    const maxSizeBytes = 25 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      setErrorMessage(
        `File size (${sizeMB}MB) exceeds the maximum allowed 25MB limit.`
      );
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    if (!title.trim()) {
      // Default title to filename without .pdf
      const cleanTitle = file.name.replace(/\.pdf$/i, '').replace(/[-_]/g, ' ');
      setTitle(cleanTitle);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage('Please select a PDF file to upload.');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setErrorMessage(null);

    try {
      const result = await adminCatalogService.uploadChapterPDF(
        chapter.id,
        selectedFile,
        title,
        (progress) => {
          setUploadProgress(progress);
        }
      );
      onSuccess(result);
    } catch (err: unknown) {
      const serverMsg =
        (err as { response?: { data?: { error?: string } } }).response?.data?.error ||
        (err instanceof Error ? err.message : 'Failed to upload PDF.');
      setErrorMessage(serverMsg);
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-xs p-4 animate-in fade-in-50">
      <div className="bg-white rounded-3xl shadow-2xl max-w-lg w-full p-6 sm:p-8 border border-slate-200">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <span className="text-[10px] font-black uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-md">
              Ch {chapter.chapter_number}: {chapter.title}
            </span>
            <h3 className="text-lg font-bold text-slate-900 mt-1">Upload Chapter PDF Material</h3>
          </div>
          <button
            onClick={onClose}
            disabled={isUploading}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="mt-4 p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-2xl flex items-start space-x-2 text-xs">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <p className="flex-1 font-semibold">{errorMessage}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {/* Drag & Drop Zone */}
          {!selectedFile ? (
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-3xl p-8 text-center cursor-pointer transition-all ${
                dragActive
                  ? 'border-indigo-600 bg-indigo-50/50 scale-[1.01]'
                  : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50/60'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileChange}
                className="hidden"
              />
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto mb-3">
                <UploadCloud className="w-6 h-6" />
              </div>
              <p className="text-sm font-bold text-slate-800">
                Drag and drop your study note PDF here
              </p>
              <p className="text-xs text-slate-400 mt-1">
                or <span className="text-indigo-600 font-semibold underline">browse files</span> from your computer
              </p>
              <p className="text-[11px] text-slate-400 mt-3 font-medium">
                Accepts strictly <strong className="text-slate-600">.pdf</strong> format (Max size: 25MB)
              </p>
            </div>
          ) : (
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-between">
              <div className="flex items-center space-x-3 truncate mr-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="truncate">
                  <p className="text-xs font-bold text-slate-900 truncate">{selectedFile.name}</p>
                  <p className="text-[11px] text-slate-400">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • PDF Document
                  </p>
                </div>
              </div>
              {!isUploading && (
                <button
                  type="button"
                  onClick={() => setSelectedFile(null)}
                  className="p-1.5 text-slate-400 hover:text-rose-600 transition"
                  title="Remove file"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          )}

          {/* Title Field */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              Material Display Title
            </label>
            <input
              type="text"
              placeholder="e.g. Complete Formula Sheet & Concept Notes"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isUploading}
              className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600 disabled:opacity-50"
            />
          </div>

          {/* Progress Bar (Acceptance Criterion: Progress bar for file upload) */}
          {isUploading && (
            <div className="space-y-1.5 pt-2">
              <div className="flex justify-between text-xs font-bold text-slate-700">
                <span className="flex items-center">
                  <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin text-indigo-600" />
                  {uploadProgress < 100 ? 'Uploading PDF file...' : 'Processing & encrypting...'}
                </span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-indigo-600 transition-all duration-200 rounded-full"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Modal Actions */}
          <div className="pt-4 flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isUploading}
              className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-xs font-bold hover:bg-slate-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isUploading || !selectedFile}
              className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-xs transition flex items-center space-x-1.5 cursor-pointer"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Uploading ({uploadProgress}%)...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-3.5 h-3.5" />
                  <span>Upload PDF</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
