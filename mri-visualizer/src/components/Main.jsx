import React, { useState } from 'react';
import NpyVisualizer from './NpyVisualizer';

const Main = () => {
    const [imageFiles, setImageFiles] = useState({});
    const [loading, setLoading] = useState(false);
    const [showVisualizer, setShowVisualizer] = useState(false);
    const [currentModality, setCurrentModality] = useState('modality_1'); // Default to the first modality

    const handleFileChange = (event) => {
        const files = event.target.files;
        const niiGzFiles = Array.from(files).filter(file => file.name.endsWith('.nii.gz'));

        if (niiGzFiles.length > 0) {
            processNiftiFiles(niiGzFiles);
        } else {
            console.log('No .nii.gz files found in the selected folder.');
        }
    };

    const processNiftiFiles = async (files) => {
        const formData = new FormData();
        files.forEach(file => formData.append('file', file)); // Use 'file' as the key for the backend

        setLoading(true);
        try {
            const response = await fetch('http://localhost:4000/process_nii', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Failed to process NIfTI files');
            }

            const data = await response.json();
            setImageFiles(data); // Store the resulting images for all modalities
            setShowVisualizer(true);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const handleModalityChange = (modality) => {
        setCurrentModality(modality);
    };

    return (
        <main>
            {!showVisualizer ? (
                <>
                    <h2>Upload MRI Samples</h2>
                    <input 
                        type="file" 
                        webkitdirectory="true" 
                        directory="true" 
                        onChange={handleFileChange} 
                    />
                    {loading && <p>Processing files, please wait...</p>}
                </>
            ) : (
                <div>
                    <h2>2D Slices Visualization</h2>
                    <div>
                        <button onClick={() => handleModalityChange('modality_1')}>Modality 1</button>
                        <button onClick={() => handleModalityChange('modality_2')}>Modality 2</button>
                        <button onClick={() => handleModalityChange('modality_3')}>Modality 3</button>
                        <button onClick={() => handleModalityChange('modality_4')}>Modality 4</button>
                        <button onClick={() => handleModalityChange('segmentation')}>Segmentation</button>
                    </div>
                    {imageFiles[currentModality] && imageFiles[currentModality].map((slice, index) => (
                        <img style={{ width: '100px', height: '100px', margin: '10px' }} key={index} src={`data:image/jpeg;base64,${slice}`} alt={`Slice ${index + 1}`} />
                    ))}
                </div>
            )}
        </main>
    );
};

export default Main;
