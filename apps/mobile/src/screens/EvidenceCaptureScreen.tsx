import React, { useState, useRef, useEffect } from 'react';
import { View, StyleSheet, TouchableOpacity, Image, Alert } from 'react-native';
import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import { X, RefreshCcw, UploadCloud } from 'lucide-react-native';
import { Button, Text, YStack, XStack, Spinner } from 'tamagui';
import * as FileSystem from 'expo-file-system';
import * as Crypto from 'expo-crypto';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { IncidentsApi, EvidenceIntentRequest } from '@incident-ledger/api-client';
import { getDb } from '../db';
import { processQueue } from '../sync/engine';

export function EvidenceCaptureScreen() {
  const router = useRouter();
  const { incidentId, photoCount } = useLocalSearchParams<{ incidentId: string; photoCount: string }>();
  const currentCount = parseInt(photoCount || '0', 10) + 1;

  const [facing, setFacing] = useState<CameraType>('back');
  const [permission, requestPermission] = useCameraPermissions();
  const [capturedPhoto, setCapturedPhoto] = useState<{ uri: string; width: number; height: number } | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const cameraRef = useRef<CameraView>(null);

  useEffect(() => {
    if (!permission) {
      requestPermission();
    }
  }, [permission]);

  if (!permission) {
    return <View style={styles.container} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.container}>
        <YStack f={1} ai="center" jc="center" p="$4" gap="$4">
          <Text ta="center">We need your permission to show the camera to capture evidence.</Text>
          <Button onPress={requestPermission}>Grant Permission</Button>
          <Button theme="alt2" onPress={() => router.back()}>Cancel</Button>
        </YStack>
      </View>
    );
  }

  function toggleCameraFacing() {
    setFacing(current => (current === 'back' ? 'front' : 'back'));
  }

  async function takePicture() {
    if (cameraRef.current) {
      try {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.8,
          // We can resize if needed, but quality 0.8 usually keeps it under 10MB
        });
        if (photo) {
          setCapturedPhoto(photo);
        }
      } catch (e) {
        Alert.alert('Error', 'Failed to capture photo');
      }
    }
  }

  async function computeSha256(uri: string): Promise<string> {
    const fileInfo = await FileSystem.getInfoAsync(uri);
    if (!fileInfo.exists) throw new Error("File does not exist");
    // Read file as base64 and hash
    const base64Str = await FileSystem.readAsStringAsync(uri, { encoding: FileSystem.EncodingType.Base64 });
    const digest = await Crypto.digestStringAsync(
      Crypto.CryptoDigestAlgorithm.SHA256,
      base64Str,
      { encoding: Crypto.CryptoEncoding.HEX }
    );
    return digest;
  }

  async function usePhoto() {
    if (!capturedPhoto || !incidentId) return;
    setIsUploading(true);
    
    try {
      const fileInfo = await FileSystem.getInfoAsync(capturedPhoto.uri);
      if (!fileInfo.exists) throw new Error("File not found");
      const byteSize = fileInfo.size;
      
      if (byteSize > 10 * 1024 * 1024) {
        Alert.alert('Error', 'Photo size exceeds 10MB limit. Please retake.');
        setCapturedPhoto(null);
        return;
      }
      
      const mediaType = 'image/jpeg';
      const sha256 = await computeSha256(capturedPhoto.uri);
      
      const isOnline = true; // In a real app, check useNetInfo() or global session state
      
      if (isOnline) {
        // Online Flow
        const intentReq: EvidenceIntentRequest = { media_type: mediaType, byte_size: byteSize };
        const intentRes = await IncidentsApi.createEvidenceIntentEndpoint(incidentId, "00000000-0000-0000-0000-000000000000", intentReq);
        
        const uploadRes = await FileSystem.uploadAsync(intentRes.upload_url, capturedPhoto.uri, {
          httpMethod: 'PUT',
          headers: {
            'Content-Type': mediaType
          }
        });
        
        if (uploadRes.status < 200 || uploadRes.status >= 300) {
          throw new Error(`Upload failed with status ${uploadRes.status}`);
        }
        
        await IncidentsApi.finalizeEvidenceEndpoint(incidentId, intentRes.evidence_id, "00000000-0000-0000-0000-000000000000", {
          client_sha256: sha256
        });
        
        // Return to wizard
        router.back();
      } else {
        // Offline Flow
        const evidenceId = Crypto.randomUUID();
        const db = await getDb();
        const now = new Date().toISOString();
        
        await db.runAsync(
          `INSERT INTO local_evidence (id, incident_id, local_file_path, sha256, media_type, byte_size, upload_status, captured_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
          [evidenceId, incidentId, capturedPhoto.uri, sha256, mediaType, byteSize, 'pending', now]
        );
        
        // Enqueue operation
        const opId = Crypto.randomUUID();
        await db.runAsync(
          `INSERT INTO local_operations (id, entity_id, operation_type, payload_encrypted, payload_sha256, state, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)`,
          [opId, evidenceId, 'evidence_intent', '', '', 'pending', now]
        );
        
        // Trigger sync engine silently
        processQueue().catch(console.error);
        
        router.back();
      }
    } catch (e: any) {
      console.error(e);
      Alert.alert('Upload Error', e.message || 'Failed to process evidence');
    } finally {
      setIsUploading(false);
    }
  }

  if (capturedPhoto) {
    return (
      <View style={styles.container}>
        <Image source={{ uri: capturedPhoto.uri }} style={styles.preview} />
        {isUploading && (
          <View style={styles.overlay}>
            <Spinner size="large" color="$color" />
            <Text mt="$2" color="white" fow="bold">Uploading Securely...</Text>
          </View>
        )}
        {!isUploading && (
          <View style={styles.controls}>
            <XStack jc="space-between" ai="center" w="100%" px="$6">
              <TouchableOpacity style={styles.button} onPress={() => setCapturedPhoto(null)}>
                <RefreshCcw color="white" size={24} />
                <Text color="white" mt="$2">Retake</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.buttonMain} onPress={usePhoto}>
                <UploadCloud color="white" size={32} />
                <Text color="white" mt="$2" fow="bold">Use Photo</Text>
              </TouchableOpacity>
            </XStack>
          </View>
        )}
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView style={styles.camera} facing={facing} ref={cameraRef}>
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => router.back()} style={styles.iconBtn}>
            <X color="white" size={28} />
          </TouchableOpacity>
          <View style={styles.counterBadge}>
            <Text color="white" fow="bold">Photo {currentCount} of 5</Text>
          </View>
          <View style={{ width: 44 }} />
        </View>
        <View style={styles.controls}>
          <XStack jc="space-around" ai="center" w="100%">
            <View style={{ width: 64 }} />
            <TouchableOpacity style={styles.captureButton} onPress={takePicture}>
              <View style={styles.captureInner} />
            </TouchableOpacity>
            <TouchableOpacity style={styles.iconBtn} onPress={toggleCameraFacing}>
              <RefreshCcw color="white" size={28} />
            </TouchableOpacity>
          </XStack>
        </View>
      </CameraView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'black',
  },
  camera: {
    flex: 1,
    justifyContent: 'space-between',
  },
  preview: {
    flex: 1,
    resizeMode: 'contain',
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 60,
    paddingHorizontal: 20,
  },
  counterBadge: {
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  controls: {
    paddingBottom: 50,
    paddingTop: 20,
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  captureButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  captureInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: 'white',
  },
  iconBtn: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  button: {
    alignItems: 'center',
  },
  buttonMain: {
    alignItems: 'center',
    backgroundColor: '$blue10Light',
    padding: 16,
    borderRadius: 12,
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  }
});
