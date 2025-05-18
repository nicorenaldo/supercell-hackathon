import { Canvas } from '@react-three/fiber';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { Experience } from './components/Experience';
import { UIOverlay } from './components/UIOverlay';
import { TextToSpeechProvider } from './contexts/TextToSpeechContext';
import { WebsocketProvider, useWebsocket } from './contexts/WebsocketContext';

// Create a wrapper component that can access the WebsocketContext
const AppContent = () => {
  const { gameID } = useWebsocket();

  return (
    <>
      <UIOverlay />
      <Canvas camera={{ fov: 30, position: [0, 0, 48] }}>
        <color attach='background' args={['#ececec']} />
        <Experience />
      </Canvas>
      <ToastContainer />
    </>
  );
};

function App() {
  return (
    <WebsocketProvider>
      <TextToSpeechProvider>
        <AppContent />
      </TextToSpeechProvider>
    </WebsocketProvider>
  );
}

export default App;
