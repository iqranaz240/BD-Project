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
        <main style={{width: '1450px', alignItems: 'center', alignSelf: 'center', textAlign: 'center', margin: 'auto auto'}}>
            {!showVisualizer ? (
                <>
                    <h3>Upload MRI Samples</h3>
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
                    <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginTop: '60px', position: 'fixed', top: '60px', left: '50%', transform: 'translateX(-50%)' }}>
                        <button onClick={() => handleModalityChange('modality_1')}>T1 Native</button>
                        <button onClick={() => handleModalityChange('modality_2')}>T2 FLAIR</button>
                        <button onClick={() => handleModalityChange('modality_3')}>T1 Contrast</button>
                        <button onClick={() => handleModalityChange('modality_4')}>T2 Weighted</button>
                        <button onClick={() => handleModalityChange('segmentation')}>Segmentation</button>
                    </div>
                    <div style={{ marginTop: '450px', display: 'flex', flexWrap: 'wrap', justifyContent: 'center', marginBottom: '100px'}}>
                    {imageFiles[currentModality] && imageFiles[currentModality].map((slice, index) => (
                        <img style={{ width: '100px', height: '100px', margin: '10px' }} key={index} src={`data:image/jpeg;base64,${slice}`} alt={`Slice ${index + 1}`} />
                    ))}
                    </div>
                </div>
            )}
        </main>
    );
};

export default Main;
