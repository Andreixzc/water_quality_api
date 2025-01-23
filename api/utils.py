import ee
from io import BytesIO
import joblib
from io import BytesIO
import hashlib

def initialize_ee():
    try:
        ee.Initialize()
    except Exception as e:  # noqa
        ee.Authenticate()
        ee.Initialize()

def serialize_model(model):
    buffer = BytesIO()
    joblib.dump(model, buffer)
    return buffer.getvalue()

def deserialize_model(binary_data):
    buffer = BytesIO(binary_data)
    return joblib.load(buffer)


def compute_file_hash(file):
    sha256_hash = hashlib.sha256()
    for chunk in iter(lambda: file.read(4096), b""):
        sha256_hash.update(chunk)
    file.seek(0) 
    return sha256_hash.hexdigest()