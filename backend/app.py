from flask import Flask, jsonify, request, send_from_directory, send_file, abort
from flask_cors import CORS  # Import CORS
from kafka import KafkaConsumer
import threading
import json
from pyspark.sql import SparkSession
import nibabel as nib
import numpy as np
import os
from PIL import Image
import io
import tempfile
import base64

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
messages = []
messages_lock = threading.Lock()

# Directory to save images
IMAGE_DIR = 'images'
os.makedirs(IMAGE_DIR, exist_ok=True)

def consume_kafka():
    consumer = KafkaConsumer(
        'test-topic',
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest',
        group_id='my-group',
        value_deserializer=lambda m: m.decode('utf-8') if m else None  # Decode bytes to str, don't parse JSON here
    )
    for msg in consumer:
        raw_value = msg.value
        if raw_value:
            try:
                # Attempt to parse JSON here with error handling
                data = json.loads(raw_value)
                with messages_lock:
                    messages.append(data)
                    if len(messages) > 1000:
                        messages.pop(0)
            except json.JSONDecodeError:
                # Skip invalid JSON messages silently or log them if you want
                print(f"Warning: skipping invalid JSON message: {raw_value}")

@app.route('/data')
def get_data():
    with messages_lock:
        recent_msgs = messages[-10:]
    return jsonify(recent_msgs)

@app.route('/process', methods=['POST'])
def process():
    files = request.files.getlist('files')  # Get the list of files
    image_files = []

    for file in files:
        # Create the temp directory if it doesn't exist
        temp_dir = 'temp'
        os.makedirs(temp_dir, exist_ok=True)

        # Save the file temporarily
        file_path = os.path.join(temp_dir, file.filename)
        file.save(file_path)

        # Process the .nii.gz file and generate images
        image_files.extend(process_nifti_to_images(file_path))

    print(f"Generated image files: {image_files}")  # Log the generated image files
    return jsonify(image_files)

def process_nifti_to_images(file_path):
    img = nib.load(file_path)
    data = img.get_fdata()  # Assuming data is in the shape (x, y, z)
    print(f"Data shape: {data.shape}")  # Debugging line

    image_files = []
    for i in range(data.shape[2]):  # Iterate over the z-axis
        slice_data = data[:, :, i]  # Get the 2D slice
        # Normalize and convert to uint8
        slice_data = ((slice_data - np.min(slice_data)) / (np.max(slice_data) - np.min(slice_data)) * 255).astype(np.uint8)
        image = Image.fromarray(slice_data)
        image_file_path = os.path.join(IMAGE_DIR, f'slice_{i}.png')
        image.save(image_file_path)
        image_files.append(image_file_path)
        print(f"Saved image: {image_file_path}")  # Log the saved image path

    print(f"Generated images: {image_files}")  # Debugging line
    return image_files

@app.route('/images/<int:slice_index>', methods=['GET'])
def get_image(slice_index):
    # Serve the image file based on the slice index
    filename = f'slice_{slice_index}.png'
    return send_file(os.path.join(IMAGE_DIR, filename), mimetype='image/png')

def process_files(file_paths):
    spark = SparkSession.builder.appName("MRI Processing").getOrCreate()
    results = []

    for file_path in file_paths:
        npy_file_path = process_nifti_to_npy(file_path)
        results.append(npy_file_path)

    spark.stop()
    return results

def normalize_image(image):
    """Normalize the image data to the range [0, 255]."""
    image = (image - np.min(image)) / (np.max(image) - np.min(image)) * 255
    return image.astype(np.uint8)

@app.route('/process_nii', methods=['POST'])
def process_nii():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if not file.filename.endswith(('.nii', '.nii.gz')):
        return jsonify({"error": "File must be a NIfTI file (.nii or .nii.gz)"}), 400

    contents = file.read()

    # Create a temporary file with the correct extension
    suffix = '.nii.gz' if file.filename.endswith('.nii.gz') else '.nii'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(contents)
        temp_file_path = temp_file.name

    try:
        # Load the NIfTI file from the temporary file
        img = nib.load(temp_file_path)
        img_data = img.get_fdata()
        print(f"Data shape: {img_data.shape}")  # Debugging line

        # Prepare to store all slices for each modality
        all_slices = {
            'modality_1': [],
            'modality_2': [],
            'modality_3': [],
            'modality_4': [],
            'segmentation': []
        }

        # Check the number of dimensions
        if img_data.ndim == 3:
            # Handle 3D data (single modality)
            for i in range(img_data.shape[2]):  # Iterate over z-axis
                slice_data = img_data[:, :, i]  # Get the 2D slice
                # Normalize the slice
                slice_data = normalize_image(slice_data)
                base64_image = to_base64(slice_data)
                all_slices['segmentation'].append(base64_image)  # Store in modality_1
        elif img_data.ndim == 4:
            # Handle 4D data (multiple modalities)
            for modality in range(img_data.shape[3]):  # Iterate over modalities
                for i in range(img_data.shape[2]):  # Iterate over z-axis
                    slice_data = img_data[:, :, i, modality]  # Get the 2D slice for the current modality
                    # Normalize the slice
                    slice_data = normalize_image(slice_data)
                    base64_image = to_base64(slice_data)
                    modality_key = f'modality_{modality + 1}' if modality < 4 else 'segmentation'
                    all_slices[modality_key].append(base64_image)

        return jsonify(all_slices)  # Return all slices as a dictionary
    except Exception as e:
        return jsonify({"error": f"Error processing NIfTI file: {str(e)}"}), 400
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

def to_base64(slice_img):
    """Convert a numpy array slice to a base64-encoded JPEG image."""
    img = Image.fromarray(slice_img).convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=95)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

if __name__ == '__main__':
    threading.Thread(target=consume_kafka, daemon=True).start()
    app.run(port=4000, debug=True)
