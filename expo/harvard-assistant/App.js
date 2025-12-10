import { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Alert } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import {
  Room,
  RoomEvent,
  Track,
  registerGlobals,
  AudioSession,
} from '@livekit/react-native';

registerGlobals();

const LIVEKIT_URL = 'wss://rag-eg9q823g.livekit.cloud';
const SERVER_URL = 'http://localhost:8000';

export default function App() {
  const [room] = useState(() => new Room());
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [status, setStatus] = useState('Disconnected');

  useEffect(() => {
    room.on(RoomEvent.Connected, () => {
      setConnected(true);
      setStatus('Connected');
    });

    room.on(RoomEvent.Disconnected, () => {
      setConnected(false);
      setStatus('Disconnected');
    });

    room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (track.kind === Track.Kind.Audio) {
        setStatus('Voice assistant active');
      }
    });

    return () => {
      room.disconnect();
    };
  }, []);

  const getToken = async () => {
    try {
      const response = await fetch(`${SERVER_URL}/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          room_name: 'harvard-voice-room',
          participant_name: 'mobile-user',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get token');
      }

      const data = await response.json();
      return data.token;
    } catch (error) {
      throw new Error(`Token error: ${error.message}`);
    }
  };

  const connect = async () => {
    try {
      setConnecting(true);
      setStatus('Connecting...');

      await AudioSession.startAudioSession();

      const token = await getToken();

      await room.connect(LIVEKIT_URL, token, {
        audio: true,
        video: false,
      });

      setStatus('Connected - Speak now!');
    } catch (error) {
      setStatus('Connection failed');
      Alert.alert('Error', error.message);
    } finally {
      setConnecting(false);
    }
  };

  const disconnect = async () => {
    await room.disconnect();
    await AudioSession.stopAudioSession();
    setStatus('Disconnected');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Harvard Assistant</Text>

      <View style={styles.statusContainer}>
        <View style={[
          styles.statusDot,
          { backgroundColor: connected ? '#4ade80' : '#ef4444' }
        ]} />
        <Text style={styles.status}>{status}</Text>
      </View>

      <TouchableOpacity
        style={[
          styles.button,
          connected ? styles.disconnectButton : styles.connectButton,
          connecting && styles.disabledButton
        ]}
        onPress={connected ? disconnect : connect}
        disabled={connecting}
      >
        <Text style={styles.buttonText}>
          {connecting ? 'Connecting...' : connected ? 'Disconnect' : 'Connect'}
        </Text>
      </TouchableOpacity>

      {connected && (
        <Text style={styles.hint}>
          Speak your question about Harvard University
        </Text>
      )}

      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 40,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 30,
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 10,
  },
  status: {
    fontSize: 18,
    color: '#cbd5e1',
  },
  button: {
    paddingHorizontal: 40,
    paddingVertical: 16,
    borderRadius: 12,
    minWidth: 200,
    alignItems: 'center',
  },
  connectButton: {
    backgroundColor: '#3b82f6',
  },
  disconnectButton: {
    backgroundColor: '#ef4444',
  },
  disabledButton: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  hint: {
    marginTop: 30,
    fontSize: 14,
    color: '#94a3b8',
    textAlign: 'center',
  },
});
