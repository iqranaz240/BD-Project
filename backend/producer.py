from kafka import KafkaProducer
import json
import time
import numpy as np
import os
from hdfs import InsecureClient
import tempfile
import base64
from PIL import Image
import io

# Initialize Kafka producer
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# HDFS configuration
HDFS_URL = 'http://localhost:9870'
HDFS_CLIENT = InsecureClient(HDFS_URL)

# Directory in HDFS where the .npy files are stored
HDFS_DIRECTORY = '/BraTs24_3D_Processed_Data'

def process_npy_file(npy_file_path, folder_name):
    print(f"Processing file: {npy_file_path}")
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix=".npy", delete=True) as temp_file:
        # Download the .npy file from HDFS to the temporary file
        HDFS_CLIENT.download(npy_file_path, temp_file.name, overwrite=True)
        
        # Load the .npy file from the temporary file
        data = np.load(temp_file.name)
        print(f"Data loaded with shape: {data.shape}")

    # Process the 3D data and send slices to Kafka
    for i in range(data.shape[2]):  # Iterate over the z-axis
        slice_data = data[:, :, i]  # Get the 2D slice

        # Normalize and convert to uint8
        slice_data = ((slice_data - np.min(slice_data)) / (np.max(slice_data) - np.min(slice_data)) * 255).astype(np.uint8)

        # Convert the slice to an image and then to bytes
        image = Image.fromarray(slice_data)
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")  # Save as PNG or any other format
        img_bytes = buffered.getvalue()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')  # Encode to base64 string

        # Send slice to Kafka
        if img_b64:
            message = {
                'folder_name': folder_name,
                'slice_index': i,
                'slice_data': img_b64  # Send the base64-encoded image
            }
            producer.send('mri-slices', value=message)  # Send the message as JSON
            print(f"Sent slice {i} to Kafka: {message}")  # Print the JSON message sent
        else:
            print(f"[WARN] No valid image data for slice index {i}")

def main():
    # List all folders in the HDFS directory
    folders = HDFS_CLIENT.list(HDFS_DIRECTORY)
    print(f"Folders in HDFS directory: {folders}")

    try:
        for folder in folders:
            folder_path = f"{HDFS_DIRECTORY}/{folder}"
            print(f"Processing folder: {folder_path}")

            # List all .npy files in the current folder
            npy_files = HDFS_CLIENT.list(folder_path)
            npy_files = [f for f in npy_files if f == 'mask_seg.npy']  # Only process mask_seg.npy files
            print(f"Found {len(npy_files)} mask_seg.npy files in {folder}")

            for npy_file in npy_files:
                npy_file_path = f"{folder_path}/{npy_file}"
                print(f"Processing file: {npy_file_path}")
                process_npy_file(npy_file_path, folder)
                time.sleep(2)  # Optional: Sleep to simulate real-time processing
    finally:
        producer.close()

if __name__ == "__main__":
    main()
