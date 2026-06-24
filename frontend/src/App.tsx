import { useState } from 'react';
import { LandingPage } from './components/LandingPage';
import { RecipeBuilder } from './components/RecipeBuilder';
import './index.css';

function App() {
  const [screen, setScreen] = useState<'landing' | 'wizard'>('landing');

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="retro-sun" />
      <div className="horizon-line" />
      <div className="synthwave-grid" />
      <div className="grid-fade" />
      <div className="crt-overlay" />

      {screen === 'landing' ? (
        <LandingPage onStart={() => setScreen('wizard')} />
      ) : (
        <RecipeBuilder onBack={() => setScreen('landing')} />
      )}
    </div>
  );
}

export default App;