import os
import hashlib
import structlog
from urllib.parse import urlencode

logger = structlog.get_logger(__name__)

# Base directory for local mock storage
LOCAL_STORAGE_DIR = ".local-storage"

def _get_local_path(bucket: str, object_path: str) -> str:
    """Helper to map bucket and path to a local filesystem path."""
    return os.path.join(LOCAL_STORAGE_DIR, bucket, object_path)

def generate_signed_upload_url(bucket: str, object_path: str, content_type: str, max_size: int) -> str:
    """
    Generate a pre-signed URL for uploading an object.
    In local development, this creates the directory structure and returns a mock URL.
    """
    local_path = _get_local_path(bucket, object_path)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    # We return a mock URL that the mobile client can use, or the mobile client
    # will intercept it. If it's a real signed URL, we would return a GCS URL.
    # For local dev, we could provide a local endpoint, but since the prompt
    # says "mock that writes to local filesystem", we will return a special local protocol URL
    # or rely on the mobile client to understand it. Wait, the mobile app expects to PUT.
    # Let's return a dummy URL that a hypothetical local proxy handles, or just a file:// URL?
    # Usually a local proxy like http://localhost:8000/mock-storage/... is used.
    # For now, let's return a deterministic string we can handle on the client side if needed, 
    # or just a dummy http URL. 
    # Actually, the prompt says "Generate: signed GCS upload URL (or mock for local dev)".
    # A dummy URL is fine. We will return http://localhost:8000/mock-storage/{bucket}/{object_path}
    
    url = f"http://localhost:8000/mock-storage/{bucket}/{object_path}"
    # In a real app we'd sign it, for now we just return it.
    return url

def verify_object_hash(bucket: str, object_path: str) -> str:
    """
    Verify the SHA-256 hash of an uploaded object.
    Reads the file from the local mock storage.
    """
    local_path = _get_local_path(bucket, object_path)
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Object {object_path} not found in bucket {bucket}")
        
    sha256 = hashlib.sha256()
    with open(local_path, "rb") as f:
        # Read in chunks for large files, though evidence is max 10MB
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
            
    return sha256.hexdigest()

def move_object(src_bucket: str, src_path: str, dest_bucket: str, dest_path: str) -> None:
    """
    Move an object from one bucket/path to another.
    """
    src_local = _get_local_path(src_bucket, src_path)
    dest_local = _get_local_path(dest_bucket, dest_path)
    
    if not os.path.exists(src_local):
        raise FileNotFoundError(f"Source object {src_path} not found in bucket {src_bucket}")
        
    os.makedirs(os.path.dirname(dest_local), exist_ok=True)
    os.rename(src_local, dest_local)
