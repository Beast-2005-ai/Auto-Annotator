import React, { useEffect, useState, useRef } from 'react';

interface InferenceProps {
  onBack: () => void;
}

export const Inference: React.FC<InferenceProps> = ({ onBack }) => {
  const [runs, setRuns] = useState<any[]>([]);
  const [cameras, setCameras] = useState<MediaDeviceInfo[]>([]);
  const [powerOn, setPowerOn] = useState(false);
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedCamera, setSelectedCamera] = useState(''); 
  const [streamId, setStreamId] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/runs')
      .then(res => res.json())
      .then(data => {
        const validRuns = data.runs.filter((r: any) => r.has_weights);
        setRuns(validRuns);
        if (validRuns.length > 0) setSelectedModel(validRuns[0].id);
      });
  }, []);

  const scanCameras = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      // Immediately stop the tracks so the browser doesn't hold the camera open;
      // this allows the backend OpenCV process to access the device index.
      stream.getTracks().forEach((t) => t.stop());
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(d => d.kind === 'videoinput');
      setCameras(videoDevices);
      if (videoDevices.length > 0) {
        // Use the device index ("0", "1", ...) so the backend OpenCV capture
        // can open the correct camera by integer index.
        setSelectedCamera('0');
      }
    } catch (err) {
      console.error("Camera access denied", err);
    }
  };

  useEffect(() => { scanCameras(); }, []);

  const handleExternalUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];
    
    if (!file.name.endsWith('.pt')) {
      alert("MUST BE A .PT MODEL FILE");
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/api/upload_external', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      
      if (data.status === 'success') {
        const newModel = { id: data.id, tags: [file.name] };
        setRuns(prev => [newModel, ...prev]);
        setSelectedModel(data.id);
        alert("EXTERNAL MODEL LOADED INTO SYSTEM!");
      }
    } catch (err) {
      alert("UPLOAD FAILED.");
    } finally {
      setIsUploading(false);
    }
  };

  const togglePower = async () => {
    if (!powerOn && (!selectedModel || !selectedCamera)) {
      alert("INSERT A MODEL CARTRIDGE AND SELECT A CAMERA FIRST!");
      return;
    }

    if (!powerOn) {
      const id = `${selectedModel}_${selectedCamera}_${Date.now()}`;
      setStreamId(id);
      setPowerOn(true);
      return;
    }

    // When turning off, tell backend to stop this stream
    if (streamId) {
      const formData = new FormData();
      formData.append('stream_id', streamId);
      await fetch('http://localhost:8000/api/stop_inference', {
        method: 'POST',
        body: formData,
      });
    }

    setPowerOn(false);
    setStreamId('');
  };

  const streamUrl = powerOn && streamId
    ? `http://localhost:8000/api/inference_stream?model_id=${selectedModel}&camera=${selectedCamera}&stream_id=${encodeURIComponent(streamId)}`
    : '';

  return (
    <div className="center-wrapper p-4 md:p-8 overflow-y-auto">
      <div className="w-full max-w-[1400px] flex justify-between mb-4 text-xs font-mono drop-shadow-md relative z-50">
        <button onClick={onBack} className="text-yellow-400 hover:text-white transition-colors">
          &lt; BACK TO TITLE
        </button>
      </div>

      <div className="arcade-machine">
        
        {/* TOP: Marquee */}
        <div className="arcade-marquee font-bold">
          LIVE INFERENCE ARCADE
        </div>

        <div className="arcade-body">
          {/* LEFT: Screen Bezel & Monitor */}
          <div className="arcade-bezel">
            <div className="arcade-monitor">
              {!powerOn ? (
                <div className="game-over">GAME OVER</div>
              ) : (
                <img 
                  src={streamUrl} 
                  alt="Live Inference Stream" 
                  className="w-full h-full object-cover"
                />
              )}
              <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%)] bg-[length:100%_4px] z-10 opacity-30" />
            </div>
          </div>

          {/* RIGHT: Control Panel */}
          <div className="arcade-side-panel shrink-0">
            
            {/* Model Cartridge Selection */}
            <div className="flex flex-col gap-2">
              <label className="text-yellow-400 text-xs tracking-wider">MODEL CARTRIDGE:</label>
              <select 
                className="arcade-dropdown w-full !text-xs !p-3 !border-orange-500 bg-black/80 truncate" 
                value={selectedModel} 
                onChange={(e) => setSelectedModel(e.target.value)}
                disabled={powerOn || isUploading}
              >
                {runs.length === 0 && <option value="">NO TAPES FOUND</option>}
                {runs.map(r => (
                  <option key={r.id} value={r.id}>
                    {r.tags.join(', ')}
                  </option>
                ))}
              </select>
              
              <input type="file" ref={fileInputRef} accept=".pt" className="hidden" onChange={handleExternalUpload} />
              <button 
                onClick={() => fileInputRef.current?.click()}
                disabled={powerOn || isUploading}
                className="retro-btn !m-0 !py-2 !px-4 !text-xs !bg-violet-600 !border-orange-500 w-full"
              >
                {isUploading ? 'LOADING...' : '+ UPLOAD EXTERNAL .PT'}
              </button>
            </div>

            {/* Video Source Selection */}
            <div className="flex flex-col gap-2">
              <label className="text-cyan-400 text-xs tracking-wider">VIDEO SOURCE:</label>
              <select 
                className="arcade-dropdown w-full !text-xs !p-3 !border-cyan-500 bg-black/80 truncate" 
                value={selectedCamera} 
                onChange={(e) => setSelectedCamera(e.target.value)}
                disabled={powerOn}
              >
                {cameras.length === 0 && <option value="">NO CAMERAS DETECTED</option>}
                {cameras.map((c, index) => (
                  <option key={c.deviceId} value={index.toString()}>
                    {c.label || `Camera Source ${index}`}
                  </option>
                ))}
              </select>
            </div>

            {/* Power Button */}
            <div className="flex flex-col items-center mt-6">
              <button 
                onClick={togglePower}
                className={`w-32 h-32 rounded-full border-4 shadow-xl transition-all active:scale-95 flex items-center justify-center font-bold text-2xl font-sans tracking-widest
                  ${powerOn ? 'bg-red-600 border-red-300 text-white shadow-[0_0_30px_rgba(255,0,0,1)]' 
                            : 'bg-green-500 border-green-200 text-black shadow-[0_0_20px_rgba(0,255,0,0.8)]'}`}
              >
                {powerOn ? 'STOP' : 'PLAY'}
              </button>
              <span className="text-orange-400 text-sm mt-4 font-mono tracking-widest">SYSTEM POWER</span>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};