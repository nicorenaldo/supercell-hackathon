import { Environment, OrbitControls, useTexture } from "@react-three/drei";
import { Avatar } from "./Avatar";
import { useThree } from "@react-three/fiber";
export const Experience = () => {
  
  const texture = useTexture("/textures/streetbg.jpg");
  const viewport = useThree((state) => state.viewport);
  return (
    <>
      <OrbitControls />
      
      <Avatar position={[0, -3, 5]} scale={2}/>

      <Environment preset="city" />
      <mesh>
        <planeGeometry args={[viewport.width, viewport.height]} />
        <meshBasicMaterial map={texture} side={2} />
      </mesh> 
    </>
  );
};
