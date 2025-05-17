import { Canvas } from '@react-three/fiber';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { Experience } from './components/Experience';
import { UIOverlay } from './components/UIOverlay';
import { TextToSpeechProvider } from './contexts/TextToSpeechContext';
import { WebsocketProvider } from './contexts/WebsocketContext';

function App() {
  return (
    <WebsocketProvider>
      <TextToSpeechProvider>
        <UIOverlay />
        <Canvas shadows camera={{ position: [0, 0, 8], fov: 42 }}>
          <color attach='background' args={['#ececec']} />
          <Experience />
        </Canvas>
        <ToastContainer />
      </TextToSpeechProvider>
    </WebsocketProvider>
  );
}

export default App;
