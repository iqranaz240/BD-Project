import React, { useEffect, useState } from 'react';
import axios from 'axios';

const HdfsImageViewer = () => {
    const [folders, setFolders] = useState([]);
    const [selectedFolder, setSelectedFolder] = useState(null);
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

    const handleFolderSelect = (folder) => {
        setSelectedFolder(folder);
    };

    return (
        <div style={{marginTop: '150px', width: '1450px'}}>
            <h3>HDFS File Processing</h3>
            
            {!loading && !selectedFolder &&
            <div>
            <h3>Select an MRI Sample to Process</h3>
             <select onChange={handleFolderChange}>

                <option value="">Samples</option>
                {folders.map((folder, index) => (
                    <option key={index} value={folder}>{folder}</option>
                ))}
            </select>
            </div>
            }

            {loading && <p>Loading images, please wait...</p>}

            {!loading && selectedFolder && (
                <div>
                    <h2>Processed MRI Images for {selectedFolder}</h2>
                    <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginTop: '150px' }}>
                        <button onClick={() => handleModalityChange('modality_1')}>Modality 1</button>
                        <button onClick={() => handleModalityChange('modality_2')}>Modality 2</button>
                        <button onClick={() => handleModalityChange('modality_3')}>Modality 3</button>
                        <button onClick={() => handleModalityChange('modality_4')}>Modality 4</button>
                        <button onClick={() => handleModalityChange('segmentation')}>Segmentation</button>
                    </div>
                </div>
            )}

            <div style={{ marginTop: '20px', marginBottom: '50px', display: 'flex', flexWrap: 'wrap', justifyContent: 'center' }}>
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
