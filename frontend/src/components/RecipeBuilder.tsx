import React, { useState, useRef, ChangeEvent, KeyboardEvent, useEffect } from 'react';

interface RecipeBuilderProps {
  onBack: () => void;
}

export const RecipeBuilder: React.FC<RecipeBuilderProps> = ({ onBack }) => {
  const [step, setStep] = useState(1);
  const [processingText, setProcessingText] = useState('SYSTEM COMPILING...');
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [currentTag, setCurrentTag] = useState('');
  const [error, setError] = useState('');
  
  const [runId, setRunId] = useState('');
  const [proofImages, setProofImages] = useState<string[]>([]);
  const [showGallery, setShowGallery] = useState(false);
  
  const [reviewMode, setReviewMode] = useState<'none' | 'prompt' | 'game'>('none');
  const [reviewIndex, setReviewIndex] = useState(0);
  
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    
    if (step === 3 && runId && reviewMode === 'none') {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`http://localhost:8000/api/status/${runId}`);
          const data = await res.json();
          
          if (data.status === 'COMPLETE') {
            clearInterval(interval);
            const proofsRes = await fetch(`http://localhost:8000/api/proofs/${runId}`);
            const proofsData = await proofsRes.json();
            setProofImages(proofsData.images || []);
            setStep(4);
          } else if (data.status === 'AWAITING_REVIEW') {
            clearInterval(interval);
            const proofsRes = await fetch(`http://localhost:8000/api/proofs/${runId}`);
            const proofsData = await proofsRes.json();
            setProofImages(proofsData.images || []);
            setReviewMode('prompt');
          } else {
            setProcessingText(data.status);
          }
        } catch (err) {
          console.error("Polling error", err);
        }
      }, 2000); 
    }
    
    return () => clearInterval(interval);
  }, [step, runId, reviewMode]);

  const startPhase2 = async () => {
    setReviewMode('none'); 
    setProcessingText('RESUMING PIPELINE (TRAINING 30 EPOCHS)...');
    
    const formData = new FormData();
    formData.append('run_id', runId);
    
    await fetch('http://localhost:8000/api/continue_pipeline', {
      method: 'POST',
      body: formData
    });
  };

  useEffect(() => {
    const handleKeyDown = async (e: globalThis.KeyboardEvent) => {
      if (reviewMode !== 'game') return; 
      
      const key = e.key.toUpperCase();
      if (key === 'Q' || key === 'T') {
        if (key === 'Q') {
          const currentImg = proofImages[reviewIndex];
          const filename = currentImg.split('/').pop();
          if (filename) {
            await fetch(`http://localhost:8000/api/discard/${runId}/${filename}`, { method: 'DELETE' });
          }
        }
        
        if (reviewIndex + 1 < proofImages.length) {
          setReviewIndex(prev => prev + 1);
        } else {
          startPhase2();
        }
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [reviewMode, reviewIndex, proofImages, runId]);


  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.type.startsWith('video/')) {
        setError('INVALID FORMAT. VIDEO FILES ONLY (.MP4, .MKV)');
        return;
      }
      setSelectedFile(file);
      setError('');
    }
  };

  const handleAddTag = () => {
    const cleanTag = currentTag.trim();
    if (!cleanTag) return;
    const lettersOnlyRegex = /^[a-zA-Z]+$/;
    if (!lettersOnlyRegex.test(cleanTag)) {
      setError('LETTERS ONLY. NO NUMBERS OR SYMBOLS.');
      return;
    }
    if (tags.length >= 5) {
      setError('MAX 5 TARGETS ALLOWED.');
      return;
    }
    if (tags.includes(cleanTag)) {
      setError('TARGET ALREADY EXISTS.');
      return;
    }
    setTags([...tags, cleanTag]);
    setCurrentTag('');
    setError('');
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
    if (tags.length <= 5) setError('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const executeRun = async () => {
    setError('');
    setStep(3); 
    setProcessingText('INITIALIZING PIPELINE...');

    if (!selectedFile || tags.length === 0) {
      setError('MISSING TAPE OR TARGETS');
      setStep(2);
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('tags', JSON.stringify(tags));

    try {
      const response = await fetch('http://localhost:8000/api/compile', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('PIPELINE FAILED');
      const result = await response.json();
      if (result.status === 'error') throw new Error(result.message);

      setRunId(result.run_id);
    } catch (err) {
      setError('SERVER OFFLINE OR PIPELINE CRASHED.');
      setStep(2); 
    }
  };

  const handlePlayAgain = () => {
    const confirmReset = window.confirm("WARNING: Have you downloaded the .PT file? This is a one-time session.");
    if (confirmReset) {
      setSelectedFile(null);
      setTags([]);
      setRunId('');
      setStep(1);
      setShowGallery(false);
      setReviewMode('none');
    }
  };

  const handleSafeBack = () => {
    if (step === 4) {
      const confirmExit = window.confirm("WARNING: Have you downloaded the .PT file? Leaving this screen will close the session.");
      if (confirmExit) onBack();
    } else {
      onBack();
    }
  };

  // Extract the next 3 images for the card stack
  const visibleCards = proofImages.slice(reviewIndex, reviewIndex + 3);

  return (
    <>
      <div className="center-wrapper p-8">
        <div className="w-full max-w-2xl flex justify-between mb-8 text-xs font-mono drop-shadow-md">
          <button onClick={handleSafeBack} className="text-yellow-400 hover:text-white transition-colors">
            &lt; BACK TO TITLE
          </button>
          <span className="text-pink-500 animate-pulse">STAGE {step}-4</span>
        </div>

        <div className="w-full max-w-2xl bg-black/80 border-4 border-gray-400 p-8 shadow-[8px_8px_0_rgba(0,0,0,0.7)] backdrop-blur-sm min-h-[400px] flex flex-col items-center justify-center relative">
          
          {error && (
            <div className="absolute top-4 w-[90%] bg-red-900 border-2 border-red-500 text-white text-xs p-2 text-center animate-pulse z-10">
              ⚠️ {error} ⚠️
            </div>
          )}

          {step === 1 && (
            <div className="text-center w-full flex flex-col items-center">
              <h2 className="text-yellow-400 mb-8 text-xl">STEP 1: INSERT TAPE</h2>
              <input type="file" ref={fileRef} accept="video/*" className="hidden" onChange={handleFileChange} />
              <button className="retro-btn mb-8" onClick={() => fileRef.current?.click()}>BROWSE VIDEO</button>
              {selectedFile ? (
                <p className="text-green-400 text-xs mt-4">LOCKED: {selectedFile.name}</p>
              ) : (
                <p className="text-gray-500 text-xs mt-4">WAITING FOR TAPE...</p>
              )}
              <button className="retro-btn mt-12" disabled={!selectedFile} onClick={() => { setError(''); setStep(2); }}>NEXT LEVEL</button>
            </div>
          )}

          {step === 2 && (
            <div className="text-center w-full flex flex-col items-center">
              <h2 className="text-yellow-400 mb-8 text-xl">STEP 2: DEFINE TARGETS</h2>
              <p className="text-xs text-gray-400 mb-6">({tags.length}/5 TARGETS ACQUIRED)</p>
              
              <div className="flex flex-wrap gap-4 mb-8 justify-center min-h-[40px]">
                {tags.map((tag) => (
                  <div key={tag} className="bg-gray-800 border-2 border-white p-2 text-xs flex items-center gap-2">
                    <span className="text-pink-400">{tag}</span>
                    <button onClick={() => handleRemoveTag(tag)} className="text-gray-400 hover:text-red-500 ml-2 font-bold">×</button>
                  </div>
                ))}
              </div>

              <div className="flex gap-2 w-full max-w-md justify-center">
                <input type="text" className="retro-input" placeholder="TYPE TARGET..." value={currentTag} onChange={(e) => setCurrentTag(e.target.value)} onKeyDown={handleKeyDown} disabled={tags.length >= 5} />
              </div>
              
              <div className="flex gap-4 mt-12 w-full max-w-md">
                <button className="retro-btn !bg-gray-700 !border-gray-500 text-xs" onClick={() => setStep(1)}>BACK</button>
                <button className="retro-btn text-xs" disabled={tags.length === 0} onClick={executeRun}>START COMPILE</button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="text-center w-full">
              {reviewMode === 'none' && (
                <>
                  <h2 className="text-pink-500 mb-12 text-2xl animate-pulse drop-shadow-[0_0_10px_rgba(255,0,127,0.8)]">INITIALIZING...</h2>
                  <div className="bg-black border-2 border-green-500 p-6 font-mono text-green-400 text-left h-32 flex items-center overflow-hidden">
                    <p className="text-sm">&gt; {processingText}<span className="animate-ping">_</span></p>
                  </div>
                </>
              )}

              {reviewMode === 'prompt' && (
                <div className="flex flex-col items-center">
                  <h2 className="text-yellow-400 mb-6 text-2xl drop-shadow-[0_0_10px_rgba(255,255,0,0.8)]">MANUAL CURATION</h2>
                  <p className="text-white text-sm mb-12 uppercase">Would you like to discard irrelevant images before training?</p>
                  <div className="flex gap-6 w-full justify-center">
                    <button className="retro-btn !bg-green-600 !border-white" onClick={() => { setReviewMode('game'); setReviewIndex(0); }}>YES [PLAY]</button>
                    <button className="retro-btn !bg-red-600 !border-white" onClick={startPhase2}>NO [SKIP]</button>
                  </div>
                </div>
              )}

              {/* --- UPDATED: THE CARD STACK EFFECT --- */}
              {reviewMode === 'game' && proofImages.length > 0 && (
                <div className="flex flex-col items-center w-full">
                  <h2 className="text-cyan-400 mb-2 text-xl">CURATION MINI-GAME</h2>
                  <p className="text-gray-400 text-[10px] mb-8 font-mono">IMAGE {reviewIndex + 1} OF {proofImages.length}</p>
                  
                  <div className="card-stack-container">
                    {visibleCards.map((img, idx) => (
                      <div 
                        key={reviewIndex + idx} 
                        className="stacked-card"
                        style={{
                          transform: `translateY(${idx * 15}px) scale(${1 - idx * 0.05})`,
                          zIndex: 10 - idx,
                          opacity: 1 - (idx * 0.25)
                        }}
                      >
                        <img src={img} alt="Review" className="w-full h-full object-contain" />
                      </div>
                    ))}
                  </div>

                  <div className="flex gap-12 w-full justify-center text-center font-mono mt-4">
                    <div className="flex flex-col items-center">
                      <kbd className="bg-gray-900 text-red-500 border-2 border-red-500 py-3 px-6 rounded-md text-2xl shadow-[0_0_15px_rgba(255,0,0,0.5)] mb-2">Q</kbd>
                      <span className="text-red-400 text-[10px]">DISCARD</span>
                    </div>
                    <div className="flex flex-col items-center">
                      <kbd className="bg-gray-900 text-green-500 border-2 border-green-500 py-3 px-6 rounded-md text-2xl shadow-[0_0_15px_rgba(0,255,0,0.5)] mb-2">T</kbd>
                      <span className="text-green-400 text-[10px]">SAVE (KEEP)</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {step === 4 && (
            <div className="text-center w-full flex flex-col items-center">
              <h2 className="text-green-400 mb-4 text-3xl drop-shadow-[0_0_10px_rgba(0,255,0,0.8)]">MISSION COMPLETE</h2>
              <p className="text-xs text-white mb-8">SESSION {runId} COMPILED.</p>
              
              <div className="flex flex-col gap-4 w-full max-w-xs">
                {proofImages.length > 0 && (
                  <button className="retro-btn !bg-blue-600 !border-white text-xs" onClick={() => setShowGallery(true)}>VIEW AI ANNOTATIONS</button>
                )}
                <button className="retro-btn !bg-green-600 !border-white text-xs" onClick={() => window.location.href = `http://localhost:8000/api/download/${runId}`}>DOWNLOAD .PT FILE</button>
                <button className="retro-btn !bg-gray-700 !border-gray-500 text-xs" onClick={handlePlayAgain}>PLAY AGAIN</button>
              </div>
            </div>
          )}

        </div>
      </div>

      {showGallery && (
        <div className="fixed inset-0 z-50 bg-black/95 flex flex-col items-center justify-center p-8 backdrop-blur-lg">
          <div className="w-full max-w-5xl flex justify-between items-center mb-6">
            <h2 className="text-pink-500 text-xl font-mono">GROUNDING DINO VERIFICATION LOG</h2>
            <button onClick={() => setShowGallery(false)} className="text-white text-2xl hover:text-red-500 font-sans">✖</button>
          </div>
          <div className="w-full flex-1 overflow-y-auto border-4 border-gray-600 bg-gray-900 p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 custom-scrollbar">
            {proofImages.map((src, idx) => (
              <div key={idx} className="relative group border-2 border-gray-700 hover:border-pink-500 transition-colors">
                <img src={src} alt={`Annotated frame ${idx}`} className="w-full h-auto object-cover" />
                <div className="absolute bottom-0 left-0 bg-black/80 text-green-400 text-[10px] p-1 w-full font-mono">
                  FRAME_ID_{idx.toString().padStart(3, '0')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
};