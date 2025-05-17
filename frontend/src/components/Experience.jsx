import { Environment, OrbitControls, useTexture } from "@react-three/drei";
import { Avatar } from "./Avatar";
import { useThree } from "@react-three/fiber";
export const Experience = () => {
  
  const texture = useTexture("/textures/cult.jpg");
  const viewport = useThree((state) => state.viewport);
  return (
    <>
      <OrbitControls />
      
      <Avatar position={[0, -3, 5]} scale={2}/>

      <Environment preset="forest" />
      <mesh>
        <planeGeometry args={[viewport.width + 15, viewport.height + 10]} />
        <meshBasicMaterial map={texture} side={2} />
      </mesh> 
    </>
  );
};
