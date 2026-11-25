import React, { useState, useEffect } from 'react';
import {
  X,
  Maximize2,
  Minimize2,
  Download,
  FileText,
  Lock,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { libraryService } from '../../services/libraryService';

interface PDFReaderModalProps {
  materialId: number;
  title: string;
  chapterTitle?: string;
  isFreeSample?: boolean;
  onClose: () => void;
}

export const PDFReaderModal: React.FC<PDFReaderModalProps> = ({
  materialId,
  title,
  chapterTitle,
  isFreeSample,
  onClose,
}) => {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  useEffect(() => {
    let activeUrl: string | null = null;

    const fetchPDF = async () => {
      setLoading(true);
      setError(null);
      try {
        const { url } = await libraryService.streamMaterialPDF(materialId);
        activeUrl = url;
        setPdfUrl(url);
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } }).response?.status;
        const msg = (err as { response?: { data?: { error?: string } } }).response?.data?.error;
        if (status === 403) {
          setError(
            msg ||
              'Access denied. You do not hold an active entitlement for this study material. Please purchase the corresponding chapter, subject pack, or class pass.'
          );
        } else {
          setError(msg || 'Failed to stream study material. Please try again.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchPDF();

    return () => {
      if (activeUrl) {
        URL.revokeObjectURL(activeUrl);
      }
    };
  }, [materialId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-2 sm:p-4 animate-in fade-in-50">
      <div
        className={`bg-white rounded-3xl shadow-2xl flex flex-col transition-all overflow-hidden border border-slate-200 ${
          isFullscreen
            ? 'w-full h-full rounded-none'
            : 'w-full max-w-5xl h-[88vh] max-h-[900px]'
        }`}
      >
        {/* Modal Header */}
        <div className="px-5 py-4 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center space-x-3 truncate mr-4">
            <div className="w-9 h-9 rounded-xl bg-indigo-600/30 text-indigo-400 border border-indigo-500/30 flex items-center justify-center shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div className="truncate">
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-bold text-white truncate">{title}</h3>
                {isFreeSample ? (
                  <span className="px-2 py-0.5 bg-amber-400 text-amber-950 text-[10px] font-black rounded-md flex items-center shrink-0">
                    <Sparkles className="w-3 h-3 mr-0.5" /> FREE SAMPLE
                  </span>
                ) : (
                  <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 text-[10px] font-bold rounded-md shrink-0">
                    PROTECTED STREAM
                  </span>
                )}
              </div>
              {chapterTitle && (
                <p className="text-xs text-slate-400 truncate mt-0.5">{chapterTitle}</p>
              )}
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center space-x-1.5 shrink-0">
            {pdfUrl && (
              <>
                <a
                  href={pdfUrl}
                  download={`${title}.pdf`}
                  className="p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-xl transition"
                  title="Download PDF"
                >
                  <Download className="w-4 h-4" />
                </a>
                <a
                  href={pdfUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-xl transition"
                  title="Open in new window"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              </>
            )}

            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-xl transition"
              title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>

            <button
              onClick={onClose}
              className="p-2 text-slate-300 hover:text-rose-400 hover:bg-slate-800 rounded-xl transition"
              title="Close Reader"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body / PDF Canvas */}
        <div className="flex-1 bg-slate-100 relative flex items-center justify-center overflow-hidden">
          {loading && (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="mt-4 text-sm font-bold text-slate-700">
                Streaming protected study notes...
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Decrypting and verifying active entitlements
              </p>
            </div>
          )}

          {error && (
            <div className="max-w-md p-6 bg-white rounded-3xl border border-rose-200 shadow-md text-center">
              <div className="w-12 h-12 bg-rose-50 text-rose-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Lock className="w-6 h-6" />
              </div>
              <h4 className="text-base font-bold text-slate-900">Access Restricted</h4>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">{error}</p>
              <div className="mt-6 flex justify-center space-x-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition"
                >
                  Close
                </button>
                <a
                  href="/products"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl transition"
                >
                  View Store
                </a>
              </div>
            </div>
          )}

          {!loading && !error && pdfUrl && (
            <iframe
              src={pdfUrl}
              className="w-full h-full border-0"
              title={title}
            />
          )}
        </div>
      </div>
    </div>
  );
};
