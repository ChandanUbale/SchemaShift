import { useState } from 'react';
import Step1Connect from './pages/Step1_Connect';
import Step2Discover from './pages/Step2_Discover';
import Step3Profile from './pages/Step3_Profile';
import Step4Recommend from './pages/Step4_Recommend';
import Step5DryRun from './pages/Step5_DryRun';
import Step6Migrate from './pages/Step6_Migrate';
import Step7Validate from './pages/Step7_Validate';

function App() {
  const [currentStep, setCurrentStep] = useState(1);

  // TODO: Global wizard state mapping, next/prev step controls,
  // and step-based rendering logic.

  return (
    <div>
      <h1>SchemaShift Wizard</h1>
      <p>Current Step: {currentStep}</p>
      {currentStep === 1 && <Step1Connect onNext={() => setCurrentStep(2)} />}
      {currentStep === 2 && <Step2Discover onNext={() => setCurrentStep(3)} />}
      {currentStep === 3 && <Step3Profile onNext={() => setCurrentStep(4)} />}
      {currentStep === 4 && <Step4Recommend onNext={() => setCurrentStep(5)} />}
      {currentStep === 5 && <Step5DryRun onNext={() => setCurrentStep(6)} />}
      {currentStep === 6 && <Step6Migrate onNext={() => setCurrentStep(7)} />}
      {currentStep === 7 && <Step7Validate />}
    </div>
  );
}

export default App;
