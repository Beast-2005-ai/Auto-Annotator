import React, { useEffect, useState } from 'react';

interface SavedFilesProps {
  onBack: () => void;
}

export const SavedFiles: React.FC<SavedFilesProps> = ({ onBack }) => {
  const [runs, setRuns] = useState<any[]>([]);
  const [proofImages, setProofImages] = useState<string[]>([]);
  const [showGallery, setShowGallery] = useState(false);

  useEffect(() => {
    fetch('http://localhost:8000/api/runs')
      .then(res => res.json())
      .then(data => setRuns(data.runs))
      .catch(err => console.error(err));
  }, []);

  const openGallery = async (runId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/proofs/${runId}`);
      const data = await res.json();
      setProofImages(data.images || []);
      setShowGallery(true);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="center-wrapper p-4 md:p-8">
      <div className="w-full max-w-4xl flex justify-between mb-8 text-xs font-mono drop-shadow-md">
        <button onClick={onBack} className="text-yellow-400 hover:text-white transition-colors">
          &lt; BACK TO TITLE
        </button>
        <span className="text-pink-500">SAVED SESSIONS DB</span>
      </div>

      <div className="w-full max-w-4xl bg-black/80 border-4 border-gray-400 p-6 shadow-[8px_8px_0_rgba(0,0,0,0.7)] backdrop-blur-sm h-[60vh] overflow-y-auto custom-scrollbar">
        {runs.length === 0 ? (
          <div className="text-center text-gray-500 mt-20">NO SAVED TAPE DATA FOUND.</div>
        ) : (
          <div className="flex flex-col gap-4">
            {runs.map((run) => (
              <div key={run.id} className="border-2 border-pink-500/50 p-4 bg-zinc-900/50 flex flex-col md:flex-row justify-between items-center gap-4 hover:border-pink-500 transition-colors">
                <div className="flex-1">
                  <div className="text-cyan-400 text-xs mb-2">ID: {run.id} | DATE: {run.datetime}</div>
                  <div className="flex gap-2 flex-wrap">
                    {run.tags.map((tag: string) => (
                      <span key={tag} className="bg-pink-600/30 border border-pink-500 text-pink-200 text-[10px] px-2 py-1">
                        {tag.toUpperCase()}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2 w-full md:w-auto">
                  <button 
                    onClick={() => openGallery(run.id)}
                    className="retro-btn !m-0 !py-2 !px-3 !text-[10px] !bg-blue-600 flex-1 md:flex-none"
                  >
                    ANNOTATIONS
                  </button>
                  <button 
                    disabled={!run.has_weights}
                    onClick={() => window.location.href = `http://localhost:8000/api/download/${run.id}`}
                    className="retro-btn !m-0 !py-2 !px-3 !text-[10px] !bg-green-600 flex-1 md:flex-none"
                  >
                    {run.has_weights ? 'GET .PT' : 'NO WEIGHTS'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Reusing the Gallery Modal */}
      {showGallery && (
        <div className="fixed inset-0 z-50 bg-black/95 flex flex-col items-center justify-center p-8 backdrop-blur-lg">
          <div className="w-full max-w-5xl flex justify-between items-center mb-6">
            <h2 className="text-pink-500 text-xl font-mono">VERIFICATION LOG</h2>
            <button onClick={() => setShowGallery(false)} className="text-white text-2xl hover:text-red-500">✖</button>
          </div>
          <div className="w-full flex-1 overflow-y-auto border-4 border-gray-600 bg-gray-900 p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 custom-scrollbar">
            {proofImages.length === 0 && <p className="text-red-500 col-span-3 text-center">NO IMAGES FOUND</p>}
            {proofImages.map((src, idx) => (
              <img key={idx} src={src} className="w-full h-auto border-2 border-gray-700" alt={`Frame ${idx}`} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};