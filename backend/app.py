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
from hdfs import InsecureClient

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
messages = []
messages_lock = threading.Lock()

# Directory to save images
IMAGE_DIR = 'images'
os.makedirs(IMAGE_DIR, exist_ok=True)

# HDFS configuration
HDFS_URL = 'http://localhost:9870'
HDFS_CLIENT = InsecureClient(HDFS_URL)

# Directory in HDFS where the .npy files are stored
HDFS_DIRECTORY = '/3d_preprocessed/local_output'

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

# @app.route('/images/<int:slice_index>', methods=['GET'])
# def get_image(slice_index):
#     # Serve the image file based on the slice index
#     filename = f'slice_{slice_index}.png'
#     return send_file(os.path.join(IMAGE_DIR, filename), mimetype='image/png')

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
        return jsonify({"error": "No files part"}), 400

    files = request.files.getlist('file')  # Get the list of files with the key 'file'
    if len(files) != 5:
        return jsonify({"error": "Five NIfTI files must be provided (4 modalities and 1 segmentation)."}), 400

    all_slices = {
        'modality_1': [],
        'modality_2': [],
        'modality_3': [],
        'modality_4': [],
        'segmentation': []
    }

    try:
        for file in files:
            if not file.filename.endswith(('.nii', '.nii.gz')):
                return jsonify({"error": f"File {file.filename} must be a NIfTI file (.nii or .nii.gz)"}), 400

            contents = file.read()

            # Create a temporary file with the correct extension
            suffix = '.nii.gz' if file.filename.endswith('.nii.gz') else '.nii'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(contents)
                temp_file_path = temp_file.name

            # Load the NIfTI file from the temporary file
            img = nib.load(temp_file_path)
            img_data = img.get_fdata()
            print(f"Data shape for {file.filename}: {img_data.shape}")  # Debugging line

            # Process all slices for the current modality or segmentation
            for i in range(img_data.shape[2]):  # Iterate over z-axis
                slice_data = img_data[:, :, i]  # Get the 2D slice
                # Normalize the slice
                slice_data = normalize_image(slice_data)
                base64_image = to_base64(slice_data)

                # Assign the base64 image to the correct modality or segmentation
                if 'seg' in file.filename.lower():
                    all_slices['segmentation'].append(base64_image)
                elif file.filename.endswith('t1n.nii') or file.filename.endswith('t1n.nii.gz'):
                    all_slices['modality_1'].append(base64_image)
                elif file.filename.endswith('t2f.nii') or file.filename.endswith('t2f.nii.gz'):
                    all_slices['modality_2'].append(base64_image)
                elif file.filename.endswith('t1c.nii') or file.filename.endswith('t1c.nii.gz'):
                    all_slices['modality_3'].append(base64_image)
                elif file.filename.endswith('t2w.nii') or file.filename.endswith('t2w.nii.gz'):
                    all_slices['modality_4'].append(base64_image)

            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

        return jsonify(all_slices)  # Return all slices as a dictionary
    except Exception as e:
        return jsonify({"error": f"Error processing NIfTI files: {str(e)}"}), 400

def to_base64(slice_img):
    """Convert a numpy array slice to a base64-encoded JPEG image."""
    img = Image.fromarray(slice_img).convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=95)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# @app.route('/images/<int:image_index>', methods=['GET'])
# def get_image_from_hdfs(image_index):
#     """Fetch and return the image from HDFS as a response."""
#     try:
#         # Construct the path to the .npy file in HDFS
#         npy_file_path = f"{HDFS_DIRECTORY}/{image_index}.npy"
        
#         # Read the .npy file from HDFS
#         with HDFS_CLIENT.read(npy_file_path) as reader:
#             data = np.load(reader)

#         # Convert the numpy array to an image
#         # Assuming the data is in the shape (height, width) for grayscale images
#         image = Image.fromarray(data)

#         # Save the image to a BytesIO object
#         img_byte_arr = io.BytesIO()
#         image.save(img_byte_arr, format='PNG')
#         img_byte_arr.seek(0)

#         return send_file(img_byte_arr, mimetype='image/png')

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@app.route('/folders', methods=['GET'])
def list_folders():
    """List available folders in HDFS_DIRECTORY."""
    try:
        # List files and directories in the HDFS directory
        items = HDFS_CLIENT.list(HDFS_DIRECTORY)
        print(f"Items in HDFS directory: {items}")  # Debugging line

        # Filter to get only directories
        directories = [item for item in items]  # Check for directories
        print(f"Filtered directories: {directories}")  # Debugging line

        return jsonify(directories), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



HDFS_DIRECTORY = '/3d_preprocessed/local_output'
HDFS_CLIENT = InsecureClient("http://localhost:9870", user='Lenovo')  # <-- Change 'your_hdfs_user' accordingly

def to_base64(slice_data):
    from PIL import Image
    import base64
    from io import BytesIO
    im = Image.fromarray(slice_data)
    buffered = BytesIO()
    im.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

@app.route('/images/<folder_name>', methods=['GET'])
def get_images_from_folder(folder_name):
    """Fetch and return processed images from the specified folder."""
    try:
        folder_path = f"{HDFS_DIRECTORY}/{folder_name}"
        print(f"Accessing folder: {folder_path}")

        items = HDFS_CLIENT.list(folder_path)
        npy_files = [item for item in items if item.endswith('.npy')]
        print(f"Found .npy files: {npy_files}")

        all_slices = {
            'modality_1': [],
            'modality_2': [],
            'modality_3': [],
            'modality_4': [],
            'segmentation': []
        }

        for npy_file in npy_files:
            file_path = f"{folder_path}/{npy_file}"
            print(f"Reading file: {file_path}")  # Debugging line
            try:
                with tempfile.NamedTemporaryFile(suffix=".npy", delete=True) as temp_file:
                    # Download from HDFS to temp local file
                    HDFS_CLIENT.download(file_path, temp_file.name, overwrite=True)
                    temp_file.flush()
                    data = np.load(temp_file.name)

                    print(f"Processing {npy_file} with shape: {data.shape}")

                    if data.ndim == 3:
                        for i in range(data.shape[2]):
                            slice_data = data[:, :, i]
                            min_val = np.min(slice_data)
                            max_val = np.max(slice_data)
                            if max_val - min_val > 0:
                                slice_data = ((slice_data - min_val) / (max_val - min_val) * 255).astype(np.uint8)
                            else:
                                slice_data = np.zeros_like(slice_data, dtype=np.uint8)

                            base64_image = to_base64(slice_data)

                            if 'mask' in npy_file.lower():
                                all_slices['segmentation'].append(base64_image)
                            elif npy_file.endswith('t1ce.npy'):
                                all_slices['modality_1'].append(base64_image)
                            elif npy_file.endswith('t2.npy'):
                                all_slices['modality_2'].append(base64_image)
                            elif npy_file.endswith('t1.npy'):
                                all_slices['modality_3'].append(base64_image)
                            elif npy_file.endswith('flair.npy'):
                                all_slices['modality_4'].append(base64_image)

                        print(f"Added {data.shape[2]} slices from {npy_file}.")
                    elif data.ndim == 4 and 'mask' in npy_file.lower():
                        # Special handling for 4D masks (e.g., (H, W, D, C))
                        h, w, d, c = data.shape
                        for i in range(d):  # Iterate over depth
                            # Optionally: merge all classes into one image (e.g., by max projection or overlay)
                            merged_slice = np.zeros((h, w), dtype=np.uint8)
                            for j in range(c):
                                merged_slice += (data[:, :, i, j] > 0).astype(np.uint8) * (j + 1)

                            # Normalize the merged slice
                            min_val = merged_slice.min()
                            max_val = merged_slice.max()
                            if max_val - min_val > 0:
                                merged_slice = ((merged_slice - min_val) / np.ptp(merged_slice) * 255).astype(np.uint8)
                            else:
                                merged_slice = np.zeros_like(merged_slice, dtype=np.uint8)  # Handle constant values

                            base64_mask_image = to_base64(merged_slice)
                            all_slices['segmentation'].append(base64_mask_image)

                        print(f"Added {d} merged mask slices from {npy_file}.")
                    else:
                        print(f"Warning: {npy_file} is not a 3D or supported 4D array.")

            except Exception as e:
                print(f"Error reading file {npy_file}: {str(e)}")

        return jsonify(all_slices), 200
    except Exception as e:
        return jsonify({"error": f"Error processing images: {str(e)}"}), 500

    """Fetch and return processed images from the specified folder."""
    try:
        # Construct the path to the folder in HDFS
        folder_path = f"{HDFS_DIRECTORY}/{folder_name}"
        print(f"Accessing folder: {folder_path}")  # Debugging line
        
        # List the .npy files in the folder
        items = HDFS_CLIENT.list(folder_path)
        npy_files = [item for item in items if item.endswith('.npy')]
        print(f"Found .npy files: {npy_files}")  # Debugging line

        all_slices = {
            'modality_1': [],
            'modality_2': [],
            'modality_3': [],
            'modality_4': [],
            'segmentation': []
        }

        for npy_file in npy_files:
            file_path = f"{folder_path}/{npy_file}"
            print(f"Reading file: {file_path}")  # Debugging line
            try:
                with HDFS_CLIENT.read(file_path) as reader:
                    data = np.load(reader)  # Load the 3D numpy array

                    # Debugging: Print the shape of the data
                    print(f"Processing {npy_file} with shape: {data.shape}")
                    # Check if the data is 3D
                    for i in range(data.shape[2]):  # Iterate over the z-axis
                        slice_data = data[:, :, i]  # Get the 2D slice
                        # Normalize the slice to [0, 255] for image conversion
                        min_val = np.min(slice_data)
                        max_val = np.max(slice_data)
                        if max_val - min_val > 0:  # Avoid division by zero
                            slice_data = ((slice_data - min_val) / (max_val - min_val) * 255).astype(np.uint8)
                        else:
                            slice_data = np.zeros_like(slice_data, dtype=np.uint8)  # Handle constant values

                            base64_image = to_base64(slice_data)

                            # Assign the base64 image to the correct modality based on the filename
                            if 'mask' in npy_file.lower():
                                for j in range(img_data.shape[3]):  # Iterate over the 4th dimension
                                    mask_slice = img_data[:, :, i, j]  # Get the 2D slice for each class
                                    mask_slice = normalize_image(mask_slice)
                                    base64_mask_image = to_base64(mask_slice)
                                    all_slices['segmentation'].append(base64_mask_image)
                            elif npy_file.endswith('t1ce.npy'):
                                all_slices['modality_1'].append(base64_image)
                            elif npy_file.endswith('t2.npy'):
                                all_slices['modality_2'].append(base64_image)
                            elif npy_file.endswith('t1.npy'):
                                all_slices['modality_3'].append(base64_image)
                            elif npy_file.endswith('flair.npy'):
                                all_slices['modality_4'].append(base64_image)

                        # Debugging: Print how many slices were added for this file
                        print(f"Added {data.shape[2]} slices from {npy_file}.")
            except Exception as e:
                print(f"Error reading file {npy_file}: {str(e)}")  # Debugging line


        return jsonify(all_slices), 200  # Return all slices as a dictionary
    except Exception as e:
        return jsonify({"error": f"Error processing images: {str(e)}"}), 500

if __name__ == '__main__':
    threading.Thread(target=consume_kafka, daemon=True).start()
    app.run(port=4000, debug=True)
