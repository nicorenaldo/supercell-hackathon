// hooks/useGame.js
import { useEffect, useRef, useState } from 'react'

export function useGame() {
  const socketRef = useRef(null)
  const [messages, setMessages] = useState([])
  const [gameOver, setGameOver] = useState(false)
  const [achievements, setAchievements] = useState([])

  // 1️⃣ Trigger /start-game on mount
  useEffect(() => {
    fetch('http://localhost:8000/start-game', { method: 'POST' })
      .then(res => {
        if (!res.ok) throw new Error('start-game failed')
        console.log('✅ Game started')
      })
      .catch(console.error)
  }, [])

  // 2️⃣ Open WebSocket
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws')
    socketRef.current = ws

    ws.onopen = () => console.log('🟢 WS connected')
    ws.onmessage = ({ data }) => {
      try {
        const msg = JSON.parse(data)
        if (msg.dialog && msg.npc) {
          setMessages(m => [...m, `${msg.npc}: ${msg.dialog}`])
        } else if (msg.game_over) {
          setGameOver(true)
        } else if (msg.achievement_unlocked) {
          setAchievements(a => [...a, ...msg.achievement_unlocked])
        }
      } catch (e) { console.error('WS parse error', e) }
    }
    ws.onerror = console.error
    ws.onclose = () => console.log('🔴 WS closed')

    return () => ws.close()
  }, [])

  // 3️⃣ Recording controls
  const startRecording = () =>
    fetch('http://localhost:8000/recording/start', { method: 'POST' })

  const stopRecording = () =>
    fetch('http://localhost:8000/recording/stop', { method: 'POST' })

  return { messages, gameOver, achievements, startRecording, stopRecording }
}
