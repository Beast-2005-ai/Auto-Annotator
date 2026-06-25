import { useState } from 'react';
import { LandingPage } from './components/LandingPage';
import { RecipeBuilder } from './components/RecipeBuilder';
import { SavedFiles } from './components/SavedFiles';
import { Inference } from './components/Inference';
import './index.css';

// Expand the AppScreen types
type AppScreen = 'landing' | 'wizard' | 'saved' | 'inference';

function App() {
  const [screen, setScreen] = useState<AppScreen>('landing');

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="retro-sun" />
      <div className="horizon-line" />
      <div className="synthwave-grid" />
      <div className="grid-fade" />
      <div className="crt-overlay" />

      {screen === 'landing' && <LandingPage setScreen={setScreen} />}
      {screen === 'wizard' && <RecipeBuilder onBack={() => setScreen('landing')} />}
      {screen === 'saved' && <SavedFiles onBack={() => setScreen('landing')} />}
      {screen === 'inference' && <Inference onBack={() => setScreen('landing')} />}
    </div>
  );
}

export default App;