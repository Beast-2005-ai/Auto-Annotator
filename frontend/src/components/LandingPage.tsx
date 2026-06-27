import React from 'react';

interface LandingPageProps {
  setScreen: (screen: 'landing' | 'wizard' | 'saved' | 'inference' | 'logs') => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ setScreen }) => {
  return (
    <div className="center-wrapper">
      <div className="mb-12 text-center bg-black/60 p-8 rounded-xl border-2 border-pink-500/50 shadow-[0_0_20px_rgba(255,0,127,0.3)]">
        <h1 className="text-4xl md:text-6xl mb-4 text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-orange-400 drop-shadow-[2px_2px_0_rgba(0,0,0,1)]">
          AI PIPELINE
        </h1>
        <h2 className="text-sm md:text-xl text-yellow-400 drop-shadow-[2px_2px_0_rgba(0,0,0,1)]">
          MACHINE LEARNING TERMINAL
        </h2>
      </div>

      <div className="flex flex-col items-center w-full">
        <button onClick={() => setScreen('wizard')} className="retro-btn">PLAY (TRAIN)</button>
        <button onClick={() => setScreen('saved')} className="retro-btn">SAVED SESSIONS</button>
        <button onClick={() => setScreen('inference')} className="retro-btn">INFERENCE</button>
        {/* Swapped Exit for Logs */}
        <button onClick={() => setScreen('logs')} className="retro-btn">SYSTEM LOGS</button>
      </div>

      <div className="absolute bottom-8 text-xs text-cyan-300 animate-pulse bg-black/50 px-4 py-2 border border-cyan-500">
        INSERT COIN TO CONTINUE
      </div>
    </div>
  );
};