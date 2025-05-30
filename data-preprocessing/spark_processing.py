from pyspark.sql import SparkSession
import nibabel as nib
import numpy as np
import os
import glob
from sklearn.preprocessing import MinMaxScaler
from scipy.ndimage import zoom
import time

# --- Configuration ---
TRAIN_DATASET_PATH = 'D:\\MS-Thesis\\dataset\\training_data\\'
LOCAL_OUTPUT_DIR = 'D:\\MS-Thesis\\local_output'

# --- File Lists ---
t1_list = sorted(glob.glob(TRAIN_DATASET_PATH + '*/*-t1n.nii.gz'))[:100]
t2_list = sorted(glob.glob(TRAIN_DATASET_PATH + '*/*-t2w.nii.gz'))[:100]
t1ce_list = sorted(glob.glob(TRAIN_DATASET_PATH + '*/*-t1c.nii.gz'))[:100]
flair_list = sorted(glob.glob(TRAIN_DATASET_PATH + '*/*-t2f.nii.gz'))[:100]
mask_list = sorted(glob.glob(TRAIN_DATASET_PATH + '*/*-seg.nii.gz'))[:100]

# --- Utils ---
def normalize_volume(volume):
    scaler = MinMaxScaler()
    flat = volume.reshape(-1, 1)
    scaled = scaler.fit_transform(flat).reshape(volume.shape)
    return scaled

def resize_volume(volume, target_shape=(256, 256, 160), order=3):
    zoom_factors = [t / s for t, s in zip(target_shape, volume.shape)]
    return zoom(volume, zoom_factors, order=order)

def to_categorical_np(y, num_classes):
    shape = y.shape
    y_flat = y.flatten()
    one_hot = np.zeros((y_flat.size, num_classes), dtype=np.uint8)
    one_hot[np.arange(y_flat.size), y_flat] = 1
    return one_hot.reshape(*shape, num_classes)

def get_patient_name(path):
    return os.path.basename(os.path.dirname(path))

def process_volume(idx):
    try:
        # --- Load Volumes ---
        t1 = nib.load(t1_list[idx]).get_fdata()
        t2 = nib.load(t2_list[idx]).get_fdata()
        t1ce = nib.load(t1ce_list[idx]).get_fdata()
        flair = nib.load(flair_list[idx]).get_fdata()
        mask = nib.load(mask_list[idx]).get_fdata().astype(np.uint8)

        # --- Preprocessing ---
        mask[mask == 4] = 3
        t1 = normalize_volume(t1)
        t2 = normalize_volume(t2)
        t1ce = normalize_volume(t1ce)
        flair = normalize_volume(flair)

        # --- Crop on middle slice ---
        mid_slice = t1.shape[2] // 2
        ii = jj = ii1 = jj1 = 0
        for i in range(5, t1.shape[0] - 5):
            for j in range(5, t1.shape[1] - 5):
                if (t1[i, j, mid_slice] == 0 and t1[i-1, j, mid_slice] == 0 and
                    t1[i+1, j, mid_slice] == 0 and t1[i, j-1, mid_slice] == 0 and t1[i, j+1, mid_slice] == 0):
                    if ii1 == 0: ii = i
                else:
                    ii1 = i
        for j in range(5, t1.shape[1] - 5):
            for i in range(5, t1.shape[0] - 5):
                if (t1[i, j, mid_slice] == 0 and t1[i-1, j, mid_slice] == 0 and
                    t1[i+1, j, mid_slice] == 0 and t1[i, j-1, mid_slice] == 0 and t1[i, j+1, mid_slice] == 0):
                    if jj1 == 0: jj = j
                else:
                    jj1 = j

        t1 = resize_volume(t1[ii:ii1, jj:jj1, 13:141], (256, 256, 128))
        t2 = resize_volume(t2[ii:ii1, jj:jj1, 13:141], (256, 256, 128))
        t1ce = resize_volume(t1ce[ii:ii1, jj:jj1, 13:141], (256, 256, 128))
        flair = resize_volume(flair[ii:ii1, jj:jj1, 13:141], (256, 256, 128))
        mask = resize_volume(mask[ii:ii1, jj:jj1, 13:141], (256, 256, 128), order=0)
        mask = np.rint(mask).astype(np.uint8)
        mask[mask > 3] = 3
        mask = to_categorical_np(mask, 4)

        # --- Save Output ---
        patient_name = get_patient_name(t1_list[idx])
        out_dir = os.path.join(LOCAL_OUTPUT_DIR, patient_name)
        os.makedirs(out_dir, exist_ok=True)

        np.save(os.path.join(out_dir, 'image_t1n.npy'), t1)
        np.save(os.path.join(out_dir, 'image_t2w.npy'), t2)
        np.save(os.path.join(out_dir, 'image_t1c.npy'), t1ce)
        np.save(os.path.join(out_dir, 'image_t2f.npy'), flair)
        np.save(os.path.join(out_dir, 'mask_seg.npy'), mask)

        return f"Processed {patient_name}"
    except Exception as e:
        return f"Failed processing index {idx}: {e}"

if __name__ == '__main__':
    spark = SparkSession.builder.appName("NIfTI Processing").getOrCreate()
    indices = spark.sparkContext.parallelize(range(len(t1_list)))
    indices.foreach(lambda i: process_volume(i))
    spark.stop()
