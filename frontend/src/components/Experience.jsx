import { Environment, OrbitControls, useTexture } from '@react-three/drei';
import { useThree } from '@react-three/fiber';
import { Avatar } from './Avatar';
export const Experience = () => {
  const texture = useTexture('/textures/cult.jpg');
  const viewport = useThree((state) => state.viewport);
  return (
    <>
      <OrbitControls />

      <Avatar position={[0, -1, 35]} scale={2} />

      <Environment preset='forest' />
      <mesh>
        <planeGeometry args={[viewport.width + 15, viewport.height + 10]} />
        <meshBasicMaterial map={texture} side={2} />
      </mesh>
    </>
  );
};
