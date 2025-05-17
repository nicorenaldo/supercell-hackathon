import { Canvas } from '@react-three/fiber';
import { Experience } from './components/Experience';
import { UIOverlay } from './components/UIOverlay';

function App() {
  return (
    <>
      <UIOverlay />
      <Canvas
        shadows
        camera={{ position: [0, 0, 8], fov: 42 }}
        // className='absolute inset-0 z-0'
      >
        <color attach='background' args={['#ececec']} />
        <Experience />
      </Canvas>
    </>
  );
}

export default App;
