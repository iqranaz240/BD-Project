import React, { useEffect, useState } from 'react';
import * as THREE from 'three';
import NpyLoader from 'npyjs'; // Import the npy loader

const NpyVisualizer = ({ npyFiles }) => {
    const [imageFiles, setImageFiles] = useState([]);
    const [currentSlice, setCurrentSlice] = useState(0);

    useEffect(() => {
        const loadImages = async () => {
            const response = await fetch('http://localhost:5000/process', {
                method: 'POST',
                body: JSON.stringify({ files: npyFiles }),
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            const images = await response.json();
            setImageFiles(images);
        };

        loadImages();
    }, [npyFiles]);

    const handleSliceChange = (direction) => {
        if (direction === 'next') {
            setCurrentSlice((prev) => (prev + 1) % imageFiles.length);
        } else {
            setCurrentSlice((prev) => (prev - 1 + imageFiles.length) % imageFiles.length);
        }
    };

    return (
        <div>
            <h2>2D Slices Visualization</h2>
            {imageFiles.length > 0 && (
                <div>
                    <h3>Slice {currentSlice + 1} of {imageFiles.length}</h3>
                    <img src={`http://localhost:5000/images/${currentSlice}`} alt={`Slice ${currentSlice + 1}`} />
                    <div>
                        <button onClick={() => handleSliceChange('prev')}>Previous Slice</button>
                        <button onClick={() => handleSliceChange('next')}>Next Slice</button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default NpyVisualizer;
