import os
import glob
import nibabel as nib
import numpy as np
import cv2
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.utils import to_categorical
from scipy.ndimage import zoom
import time

# Paths
TRAIN_DATASET_PATH = 'D:\\MS-Thesis\\dataset\\training_data\\'
OUTPUT_ROOT = 'D:\\BraTS2024\\processing_data\\'

os.makedirs(OUTPUT_ROOT, exist_ok=True)

# Load file lists (limit 30)
t1_list = sorted(glob.glob(TRAIN_DATASET_PATH + '*/*-t1n.nii.gz'))[:30]
t2_list = sorted(glob.glob(TRAIN_DATASET_PATH + '*/*-t2w.nii.gz'))[:30]
t1ce_list = sorted(glob.glob(TRAIN_DATASET_PATH + '*/*-t1c.nii.gz'))[:30]
flair_list = sorted(glob.glob(TRAIN_DATASET_PATH + '*/*-t2f.nii.gz'))[:30]
mask_list = sorted(glob.glob(TRAIN_DATASET_PATH + '*/*-seg.nii.gz'))[:30]

scaler = MinMaxScaler()

def normalize_volume(volume):
    # Normalize intensities per volume to [0,1]
    flat = volume.reshape(-1, 1)
    scaled = scaler.fit_transform(flat).reshape(volume.shape)
    return scaled

def resize_volume(volume, target_shape=(256, 256, 160), order=3):
    # Resize 3D volume using scipy.ndimage.zoom
    zoom_factors = [t / s for t, s in zip(target_shape, volume.shape)]
    return zoom(volume, zoom_factors, order=order)

start_total = time.time()

for idx in range(len(t1_list)):
    start = time.time()
    print(f'Processing volume {idx+1}/{len(t1_list)}')

    # Load volumes
    t1 = nib.load(t1_list[idx]).get_fdata()
    t2 = nib.load(t2_list[idx]).get_fdata()
    t1ce = nib.load(t1ce_list[idx]).get_fdata()
    flair = nib.load(flair_list[idx]).get_fdata()
    mask = nib.load(mask_list[idx]).get_fdata().astype(np.uint8)

    # Replace label 4 with 3
    mask[mask == 4] = 3

    # Normalize intensities
    t1 = normalize_volume(t1)
    t2 = normalize_volume(t2)
    t1ce = normalize_volume(t1ce)
    flair = normalize_volume(flair)

    # Crop boundaries on middle slice of t1
    mid_slice = t1.shape[2] // 2
    ii = jj = ii1 = jj1 = 0

    for i in range(5, t1.shape[0] - 5):
        for j in range(5, t1.shape[1] - 5):
            if (t1[i, j, mid_slice] == 0 and
                t1[i - 1, j, mid_slice] == 0 and
                t1[i + 1, j, mid_slice] == 0 and
                t1[i, j - 1, mid_slice] == 0 and
                t1[i, j + 1, mid_slice] == 0):
                if ii1 == 0:
                    ii = i
            else:
                ii1 = i

    for j in range(5, t1.shape[1] - 5):
        for i in range(5, t1.shape[0] - 5):
            if (t1[i, j, mid_slice] == 0 and
                t1[i - 1, j, mid_slice] == 0 and
                t1[i + 1, j, mid_slice] == 0 and
                t1[i, j - 1, mid_slice] == 0 and
                t1[i, j + 1, mid_slice] == 0):
                if jj1 == 0:
                    jj = j
            else:
                jj1 = j

    # Crop volumes and mask
    t1_cropped = t1[ii:ii1, jj:jj1, 13:141]
    t2_cropped = t2[ii:ii1, jj:jj1, 13:141]
    t1ce_cropped = t1ce[ii:ii1, jj:jj1, 13:141]
    flair_cropped = flair[ii:ii1, jj:jj1, 13:141]
    mask_cropped = mask[ii:ii1, jj:jj1, 13:141]

    # Resize volumes
    t1_resized = resize_volume(t1_cropped, target_shape=(256, 256, t1_cropped.shape[2]), order=3)
    t2_resized = resize_volume(t2_cropped, target_shape=(256, 256, t2_cropped.shape[2]), order=3)
    t1ce_resized = resize_volume(t1ce_cropped, target_shape=(256, 256, t1ce_cropped.shape[2]), order=3)
    flair_resized = resize_volume(flair_cropped, target_shape=(256, 256, flair_cropped.shape[2]), order=3)

    # Resize mask with nearest neighbor interpolation to preserve labels
    mask_resized = resize_volume(mask_cropped, target_shape=(256, 256, mask_cropped.shape[2]), order=0)
    mask_resized = np.rint(mask_resized).astype(np.uint8)
    mask_resized[mask_resized > 3] = 3  # Clamp any out-of-range values

    # One-hot encode mask
    mask_one_hot = to_categorical(mask_resized, num_classes=4)

    # Save processed data
    out_dir = os.path.join(OUTPUT_ROOT, str(idx + 1))
    os.makedirs(out_dir, exist_ok=True)

    np.save(os.path.join(out_dir, f'image_{idx + 1}_t1.npy'), t1_resized)
    np.save(os.path.join(out_dir, f'image_{idx + 1}_t2.npy'), t2_resized)
    np.save(os.path.join(out_dir, f'image_{idx + 1}_t1ce.npy'), t1ce_resized)
    np.save(os.path.join(out_dir, f'image_{idx + 1}_flair.npy'), flair_resized)
    np.save(os.path.join(out_dir, f'mask_{idx + 1}.npy'), mask_one_hot)

    end = time.time()
    print(f'Volume {idx + 1} processed in {end - start:.2f} seconds.\n')

end_total = time.time()
print(f'All volumes processed in {end_total - start_total:.2f} seconds.')
