import React, { useEffect, useState } from 'react';
import axios from 'axios';

const HdfsImageViewer = () => {
    const [folders, setFolders] = useState([]);
    const [selectedFolder, setSelectedFolder] = useState('');
    const [images, setImages] = useState({});
    const [loading, setLoading] = useState(false);
    const [currentModality, setCurrentModality] = useState('modality_1'); // Default modality

    useEffect(() => {
        // Fetch the list of folders when the component mounts
        const fetchFolders = async () => {
            try {
                const response = await axios.get('http://localhost:4000/folders');
                setFolders(response.data);
            } catch (error) {
                console.error('Error fetching folders:', error);
            }
        };

        fetchFolders();
    }, []);

    const handleFolderChange = async (event) => {
        const folderName = event.target.value;
        setSelectedFolder(folderName);
        setLoading(true); // Start loading

        // Call the API to get images for the selected folder
        try {
            const response = await axios.get(`http://localhost:4000/images/${folderName}`);
            setImages(response.data); // Store the resulting images for all modalities
        } catch (error) {
            console.error('Error fetching images:', error);
        } finally {
            setLoading(false); // Stop loading
        }
    };

    const handleModalityChange = (modality) => {
        setCurrentModality(modality);
    };

    return (
        <div>
            <select onChange={handleFolderChange}>
                <option value="">Select a folder</option>
                {folders.map((folder, index) => (
                    <option key={index} value={folder}>{folder}</option>
                ))}
            </select>

            {loading && <p>Loading images, please wait...</p>}

            <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginTop: '20px' }}>
                <button onClick={() => handleModalityChange('modality_1')}>Modality 1</button>
                <button onClick={() => handleModalityChange('modality_2')}>Modality 2</button>
                <button onClick={() => handleModalityChange('modality_3')}>Modality 3</button>
                <button onClick={() => handleModalityChange('modality_4')}>Modality 4</button>
                <button onClick={() => handleModalityChange('segmentation')}>Segmentation</button>
            </div>

            <div style={{ marginTop: '20px', display: 'flex', flexWrap: 'wrap', justifyContent: 'center' }}>
                {images[currentModality] && images[currentModality].map((image, index) => (
                    <img 
                        style={{ width: '100px', height: '100px', margin: '10px' }} 
                        key={index} 
                        src={`data:image/png;base64,${image}`} 
                        alt={`Slice ${index + 1}`} 
                    />
                ))}
            </div>
        </div>
    );
};

export default HdfsImageViewer;
