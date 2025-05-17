import React, { useMemo, useEffect, useRef, useState } from "react";
import { useGraph } from "@react-three/fiber";
import { useAnimations, useFBX, useGLTF } from "@react-three/drei";
import { useControls } from "leva";
import { SkeletonUtils } from "three-stdlib";

export function Avatar(props) {
  const { playAudio, script } = useControls({
    playAudio: false,
    script: {
      value: "chitchat",
      options: ["chitchat"],
    },
  });

  const { animations: idleClips } = useFBX("/animations/idle.fbx")
  idleClips[0].name = "Idle" 

  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animationFrameRef = useRef();
  const audioRef = useRef(null);

  const { scene } = useGLTF("/models/cult.glb");
  const clone = useMemo(() => SkeletonUtils.clone(scene), [scene]);
  const { nodes, materials } = useGraph(clone);
 

  const meshRef = useRef();
  const group = useRef();
  const { actions } = useAnimations(idleClips, clone || null)
  
  const [animation] = useState("Idle");

  useEffect(() => {
    if (actions && actions[animation]) {
      actions[animation].reset().fadeIn(0.2).play()
      return () => {
        if (actions[animation]) {
          actions[animation].fadeOut(0.2)
        }
      }
    }
  }, [actions, animation])
 
  // ✅ Audio + mouth sync
  useEffect(() => {
    if (!playAudio) {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      cancelAnimationFrame(animationFrameRef.current);
      return;
    }

    const audio = new Audio(`./audios/${script}.mp3`);
    audioRef.current = audio;

    audioContextRef.current = new (window.AudioContext ||
      window.webkitAudioContext)();
    const source = audioContextRef.current.createMediaElementSource(audio);
    analyserRef.current = audioContextRef.current.createAnalyser();

    source.connect(analyserRef.current);
    analyserRef.current.connect(audioContextRef.current.destination);

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    let smoothedVolume = 0;

    const updateMouth = () => {
      analyserRef.current.getByteFrequencyData(dataArray);
      const rawVolume =
        dataArray.reduce((a, b) => a + b, 0) / dataArray.length / 255;
      smoothedVolume = smoothedVolume * 0.8 + rawVolume * 0.2;

      const mouthIndex = nodes.Wolf3D_Avatar.morphTargetDictionary["mouthOpen"];
      if (typeof mouthIndex !== "undefined" && meshRef.current) {
        meshRef.current.morphTargetInfluences[mouthIndex] = smoothedVolume * 3;
      }

      animationFrameRef.current = requestAnimationFrame(updateMouth);
    };

    audio.play().catch(console.error);
    updateMouth();

    return () => {
      cancelAnimationFrame(animationFrameRef.current);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
    };
  }, [playAudio, script, nodes]);
 return (
    <group ref={group} {...props} dispose={null}>
  <primitive object={clone} />
</group>


  )
}

useGLTF.preload("/models/cult.glb");
