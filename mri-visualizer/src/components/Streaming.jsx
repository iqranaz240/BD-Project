import React, { useEffect, useState } from 'react';
import io from 'socket.io-client';

const Streaming = () => {
    const [currentImage, setCurrentImage] = useState(null);
    const [currentIndex, setCurrentIndex] = useState(null);
    const [currentFolder, setCurrentFolder] = useState(null);

    useEffect(() => {
        // Connect to Socket.IO server
        const socket = io('http://localhost:5000');

        socket.on('connect', () => {
            console.log('Connected to WebSocket server');
        });

        socket.on('mri_slice', (data) => {
            setCurrentImage(data.slice_data);
            setCurrentIndex(data.slice_index);
            setCurrentFolder(data.folder_name);
        });

        socket.on('error', (error) => {
            console.error('Socket.IO error:', error);
        });

        socket.on('disconnect', () => {
            console.log('Disconnected from WebSocket server');
        });

        // Cleanup on component unmount
        return () => {
            socket.disconnect();
        };
    }, []);

    return (
        <div style={{ width: '1400px', padding: '20px', marginTop: '120px' }}>
            <h3 >Real-time MRI Slice Streaming</h3>
            {currentImage && (
                <div style={{ marginTop: '20px' }}>
                    <div style={{ marginBottom: '10px' }}>
                        <strong>Folder:</strong> {currentFolder} | <strong>Slice Index:</strong> {currentIndex}
                    </div>
                    <img 
                        src={`data:image/png;base64,${currentImage}`}
                        alt={`MRI Slice ${currentIndex}`}
                        style={{ 
                            maxWidth: '100%',
                            height: 'auto',
                            border: '1px solid #ccc',
                            borderRadius: '4px'
                        }}
                    />
                </div>
            )}
            {!currentImage && (
                <div style={{ 
                    padding: '20px', 
                    textAlign: 'center',
                    border: '4px solid #ccc',
                    borderRadius: '4px'
                }}>
                    Waiting for MRI slices...
                </div>
            )}
        </div>
    );
};

export default Streaming;
