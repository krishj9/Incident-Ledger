import * as SecureStore from 'expo-secure-store';
import CryptoJS from 'crypto-js';

const ENCRYPTION_KEY_ID = 'incident_ledger_db_key';

/**
 * Retrieves the encryption key from the secure store.
 * Generates a new one if it doesn't exist.
 */
export async function getOrGenerateEncryptionKey(): Promise<string> {
  let key = await SecureStore.getItemAsync(ENCRYPTION_KEY_ID);
  if (!key) {
    // Generate a random 256-bit key using Math.random as a fallback, 
    // ideally we'd use expo-crypto but CryptoJS handles this fine for symmetric encryption strings.
    key = CryptoJS.lib.WordArray.random(32).toString(CryptoJS.enc.Hex);
    await SecureStore.setItemAsync(ENCRYPTION_KEY_ID, key);
  }
  return key;
}

/**
 * Encrypts a JSON payload using AES and the securely stored key.
 */
export async function encryptPayload(payload: any): Promise<string> {
  if (!payload) return '';
  const key = await getOrGenerateEncryptionKey();
  const jsonStr = JSON.stringify(payload);
  const encrypted = CryptoJS.AES.encrypt(jsonStr, key).toString();
  return encrypted;
}

/**
 * Decrypts an AES encrypted payload back into a JSON object.
 */
export async function decryptPayload(encryptedText: string): Promise<any> {
  if (!encryptedText) return null;
  try {
    const key = await getOrGenerateEncryptionKey();
    const bytes = CryptoJS.AES.decrypt(encryptedText, key);
    const decryptedStr = bytes.toString(CryptoJS.enc.Utf8);
    if (!decryptedStr) return null;
    return JSON.parse(decryptedStr);
  } catch (e) {
    console.error('Failed to decrypt payload:', e);
    return null;
  }
}
