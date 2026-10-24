import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioPlayer,
  useAudioRecorder,
  useAudioRecorderState,
  useAudioPlayerStatus,
} from "expo-audio";
import { File, Paths } from "expo-file-system";

const apiUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, "");

export default function VoiceSmokeTest() {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const recorderState = useAudioRecorderState(recorder);
  const player = useAudioPlayer(null);
  const playerStatus = useAudioPlayerStatus(player);
  const [recordingUri, setRecordingUri] = useState<string | null>(null);
  const [temporaryReadbackUri, setTemporaryReadbackUri] = useState<string | null>(
    null,
  );
  const recordingUriRef = useRef<string | null>(null);
  const readbackUriRef = useRef<string | null>(null);
  const [transcript, setTranscript] = useState("");
  const [status, setStatus] = useState("Ready. This test uses record-then-upload, not live transcription.");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (playerStatus.didJustFinish && temporaryReadbackUri) {
      const file = new File(temporaryReadbackUri);
      if (file.exists) file.delete();
      readbackUriRef.current = null;
      setTemporaryReadbackUri(null);
    }
  }, [playerStatus.didJustFinish, temporaryReadbackUri]);

  useEffect(
    () => () => {
      if (recordingUriRef.current) {
        const file = new File(recordingUriRef.current);
        if (file.exists) file.delete();
      }
      if (readbackUriRef.current) {
        const file = new File(readbackUriRef.current);
        if (file.exists) file.delete();
      }
    },
    [],
  );

  async function runAction(action: () => Promise<void>) {
    setError("");
    setBusy(true);
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The voice test failed.");
    } finally {
      setBusy(false);
    }
  }

  async function startRecording() {
    await runAction(async () => {
      const permission = await AudioModule.requestRecordingPermissionsAsync();
      if (!permission.granted) {
        throw new Error("Microphone permission was not granted.");
      }
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });
      await recorder.prepareToRecordAsync();
      recorder.record();
      if (recordingUriRef.current) {
        const previousFile = new File(recordingUriRef.current);
        if (previousFile.exists) previousFile.delete();
      }
      recordingUriRef.current = null;
      setStatus("Recording. Say a short test sentence, then stop.");
      setRecordingUri(null);
      setTranscript("");
    });
  }

  async function stopRecording() {
    await runAction(async () => {
      await recorder.stop();
      if (!recorder.uri) {
        throw new Error("The recorder stopped without producing an audio file.");
      }
      recordingUriRef.current = recorder.uri;
      setRecordingUri(recorder.uri);
      setStatus("Recording ready. It remains in temporary app cache until sent or discarded.");
    });
  }

  async function playRecording() {
    await runAction(async () => {
      if (!recordingUri) throw new Error("Record a sample first.");
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false });
      player.replace({ uri: recordingUri });
      player.play();
      setStatus("Playing the temporary recording.");
    });
  }

  async function transcribeRecording() {
    await runAction(async () => {
      if (!recordingUri) throw new Error("Record a sample first.");
      if (!apiUrl) throw new Error("Set EXPO_PUBLIC_API_URL in apps/mobile/.env first.");
      const file = new File(recordingUri);
      try {
        const response = await fetch(`${apiUrl}/api/cartesia/transcribe`, {
          method: "POST",
          headers: { "Content-Type": "audio/mp4" },
          body: new Blob([await file.bytes()], { type: "audio/mp4" }),
        });
        if (!response.ok) {
          const payload = (await response.json()) as { error?: string };
          throw new Error(payload.error ?? `Transcription failed (${response.status}).`);
        }
        const payload = (await response.json()) as { text: string };
        setTranscript(payload.text);
        setStatus("Transcription complete. The local recording was discarded.");
      } finally {
        if (file.exists) file.delete();
        recordingUriRef.current = null;
        setRecordingUri(null);
      }
    });
  }

  async function playCartesiaReadback() {
    await runAction(async () => {
      if (!apiUrl) throw new Error("Set EXPO_PUBLIC_API_URL in apps/mobile/.env first.");
      const response = await fetch(`${apiUrl}/api/cartesia/readback`, {
        method: "POST",
      });
      if (!response.ok) {
        const payload = (await response.json()) as { error?: string };
        throw new Error(payload.error ?? `Readback failed (${response.status}).`);
      }
      const file = new File(Paths.cache, `phase-readback-${Date.now()}.mp3`);
      await file.write(new Uint8Array(await response.arrayBuffer()));
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false });
      player.replace({ uri: file.uri });
      player.play();
      readbackUriRef.current = file.uri;
      setTemporaryReadbackUri(file.uri);
      setStatus("Playing a temporary Cartesia readback. It is deleted after playback.");
    });
  }

  async function discardRecording() {
    if (recordingUri) {
      const file = new File(recordingUri);
      if (file.exists) file.delete();
    }
    recordingUriRef.current = null;
    setRecordingUri(null);
    setTranscript("");
    setStatus("Temporary recording discarded.");
  }

  return (
    <ScrollView contentContainerStyle={styles.screen}>
      <Text style={styles.eyebrow}>PHASE / STAGE 2 VOICE CHECK</Text>
      <Text style={styles.title}>Voice test</Text>
      <Text style={styles.body}>
        The documented Expo Go fallback records first and uploads after you stop.
        This screen does not claim to show a live transcript.
      </Text>
      {!apiUrl && (
        <Text style={styles.warning}>
          API address is not configured. Set EXPO_PUBLIC_API_URL in
          apps/mobile/.env and restart Expo.
        </Text>
      )}
      <View style={styles.card}>
        <Text style={styles.label}>MICROPHONE</Text>
        <Text style={styles.body}>
          {recorderState.isRecording ? "Recording in progress." : status}
        </Text>
        <View style={styles.buttons}>
          <ActionButton
            label="Start recording"
            disabled={busy || recorderState.isRecording}
            onPress={startRecording}
          />
          <ActionButton
            label="Stop recording"
            disabled={busy || !recorderState.isRecording}
            onPress={stopRecording}
            secondary
          />
          <ActionButton
            label="Play recording"
            disabled={busy || !recordingUri}
            onPress={playRecording}
            secondary
          />
          <ActionButton
            label="Transcribe recording"
            disabled={busy || !recordingUri || !apiUrl}
            onPress={transcribeRecording}
          />
          <ActionButton
            label="Discard recording"
            disabled={busy || !recordingUri}
            onPress={discardRecording}
            secondary
          />
        </View>
      </View>
      <View style={styles.card}>
        <Text style={styles.label}>CARTESIA READBACK</Text>
        <Text style={styles.body}>
          Generates a fixed test phrase and deletes its temporary audio file
          after playback.
        </Text>
        <ActionButton
          label="Play Cartesia readback"
          disabled={busy || !apiUrl}
          onPress={playCartesiaReadback}
        />
      </View>
      <View style={styles.card}>
        <Text style={styles.label}>EDITABLE TRANSCRIPT</Text>
        <TextInput
          accessibilityLabel="Editable test transcript"
          multiline
          onChangeText={setTranscript}
          placeholder="Your transcript will appear here after upload."
          placeholderTextColor="#806E66"
          style={styles.input}
          value={transcript}
        />
        <Text style={styles.caption}>
          Test text is held in screen memory only and is not saved.
        </Text>
      </View>
      {busy && <ActivityIndicator color="#9B1B30" />}
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
    </ScrollView>
  );
}

function ActionButton({
  label,
  onPress,
  disabled,
  secondary = false,
}: {
  label: string;
  onPress: () => void;
  disabled: boolean;
  secondary?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={() => void onPress()}
      style={[
        styles.button,
        secondary && styles.secondaryButton,
        disabled && styles.disabledButton,
      ]}
    >
      <Text style={[styles.buttonText, secondary && styles.secondaryButtonText]}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: {
    flexGrow: 1,
    backgroundColor: "#F3E9D2",
    paddingHorizontal: 20,
    paddingTop: 68,
    paddingBottom: 28,
    gap: 16,
  },
  eyebrow: {
    color: "#5A0F1C",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.5,
  },
  title: {
    color: "#2A1A14",
    fontSize: 34,
    fontWeight: "700",
  },
  body: {
    color: "#2A1A14",
    fontSize: 15,
    lineHeight: 22,
  },
  warning: {
    color: "#5A0F1C",
    fontSize: 14,
    fontWeight: "600",
  },
  card: {
    borderColor: "#C9A24B",
    borderRadius: 20,
    borderWidth: 1,
    backgroundColor: "#FFF9ED",
    padding: 16,
    gap: 12,
  },
  label: {
    color: "#5A0F1C",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.1,
  },
  buttons: {
    gap: 10,
  },
  button: {
    minHeight: 46,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 24,
    borderColor: "#C9A24B",
    borderWidth: 1,
    backgroundColor: "#9B1B30",
    paddingHorizontal: 16,
    paddingVertical: 11,
  },
  secondaryButton: {
    backgroundColor: "#FFF9ED",
  },
  disabledButton: {
    opacity: 0.45,
  },
  buttonText: {
    color: "#F3E9D2",
    fontSize: 15,
    fontWeight: "700",
  },
  secondaryButtonText: {
    color: "#5A0F1C",
  },
  input: {
    minHeight: 94,
    borderRadius: 12,
    backgroundColor: "#F3E9D2",
    color: "#2A1A14",
    fontSize: 15,
    padding: 12,
    textAlignVertical: "top",
  },
  caption: {
    color: "#5A0F1C",
    fontSize: 12,
  },
  error: {
    color: "#8A1022",
    fontSize: 14,
    fontWeight: "600",
  },
});
