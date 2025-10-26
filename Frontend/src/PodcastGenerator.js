// PodcastGenerator.jsx
import React, { useState } from 'react';
import { storage, db } from './firebase';
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage';
import { collection, addDoc, getDocs } from 'firebase/firestore';
import axios from 'axios';
import './PodcastGenerator.css';

const PodcastGenerator = () => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [podcasts, setPodcasts] = useState([]);
  const [error, setError] = useState('');

  const BACKEND_URL = 'http://localhost:8000'; // Your FastAPI backend URL

  // Handle file selection
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && (selectedFile.type === 'application/pdf' || selectedFile.type === 'text/plain' || selectedFile.name.endsWith('.txt'))) {
      setFile(selectedFile);
      setError('');
    } else {
      alert('Please select a PDF or TXT file');
      setError('Please select a PDF or TXT file');
    }
  };

  // Upload file to Firebase Storage
  const uploadToFirebase = async (file) => {
    try {
      const storageRef = ref(storage, `documents/${Date.now()}_${file.name}`);
      const snapshot = await uploadBytes(storageRef, file);
      const downloadURL = await getDownloadURL(snapshot.ref);
      return downloadURL;
    } catch (error) {
      console.error('Error uploading to Firebase:', error);
      throw new Error('Failed to upload file to storage');
    }
  };

  // Generate podcast
  const generatePodcast = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setGenerating(true);
    setError('');
    
    try {
      // Step 1: Upload file to Firebase Storage
      setUploading(true);
      const fileUrl = await uploadToFirebase(file);
      setUploading(false);

      // Step 2: Send file to backend for processing
      const formData = new FormData();
      formData.append('file', file);
      
      console.log('Sending request to backend...');
      const response = await axios.post(`${BACKEND_URL}/upload_file/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes timeout for large files
      });

      console.log('Backend response:', response.data);

      const { id, summary, podcast_script, audio_path, message } = response.data;

      if (!summary || !podcast_script) {
        throw new Error('Invalid response from server');
      }

      // Step 3: Store results in Firestore
      const podcastData = {
        fileName: file.name,
        fileUrl: fileUrl,
        summary: summary,
        podcastScript: podcast_script,
        audioPath: audio_path,
        createdAt: new Date().toISOString(),
        backendId: id // Store the backend ID for reference
      };

      console.log('Storing in Firestore...');
      const docRef = await addDoc(collection(db, 'podcasts'), podcastData);
      
      // Step 4: Update state with results
      setResult({
        id: docRef.id,
        ...podcastData
      });

      // Refresh podcast list
      fetchPodcasts();

      console.log('Podcast generated successfully!');

    } catch (error) {
      console.error('Error generating podcast:', error);
      let errorMessage = 'Error generating podcast. Please try again.';
      
      if (error.response) {
        // Server responded with error status
        errorMessage = `Server error: ${error.response.data.detail || error.response.status}`;
      } else if (error.request) {
        // Request was made but no response received
        errorMessage = 'Cannot connect to server. Please make sure your backend is running on localhost:8000';
      } else if (error.code === 'storage/unauthorized') {
        errorMessage = 'Firebase storage access denied. Check your Firebase rules.';
      } else if (error.code === 'firestore/permission-denied') {
        errorMessage = 'Firestore access denied. Check your Firebase rules.';
      }
      
      setError(errorMessage);
      alert(errorMessage);
    } finally {
      setGenerating(false);
      setUploading(false);
    }
  };

  // Fetch all podcasts from Firestore
  const fetchPodcasts = async () => {
    try {
      const querySnapshot = await getDocs(collection(db, 'podcasts'));
      const podcastsList = [];
      querySnapshot.forEach((doc) => {
        podcastsList.push({ id: doc.id, ...doc.data() });
      });
      // Sort by date, newest first
      podcastsList.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
      setPodcasts(podcastsList);
    } catch (error) {
      console.error('Error fetching podcasts:', error);
      setError('Error loading previous podcasts');
    }
  };

  // Load podcasts on component mount
  React.useEffect(() => {
    fetchPodcasts();
  }, []);

  return (
    <div className="podcast-generator">
      <div className="upload-section">
        <h2>Generate Podcast from Document</h2>
        
        {/* Error Display */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
        
        <div className="file-input-container">
          <input
            type="file"
            accept=".pdf,.txt"
            onChange={handleFileChange}
            className="file-input"
            id="file-input"
          />
          <label htmlFor="file-input" className="file-input-label">
            Choose PDF or TXT File
          </label>
          <div className="file-info">
            {file && (
              <div>
                <p><strong>Selected:</strong> {file.name}</p>
                <p><strong>Size:</strong> {(file.size / 1024 / 1024).toFixed(2)} MB</p>
                <p><strong>Type:</strong> {file.type || 'TXT'}</p>
              </div>
            )}
          </div>
        </div>

        <button 
          onClick={generatePodcast} 
          disabled={!file || generating}
          className="generate-btn"
        >
          {uploading ? 'Uploading to Firebase...' : 
           generating ? 'Generating Podcast (This may take a few minutes)...' : 
           'Generate Podcast'}
        </button>

        {/* Progress Indicators */}
        {(uploading || generating) && (
          <div className="progress-indicator">
            <div className="spinner"></div>
            <p>
              {uploading ? 'Uploading file to Firebase...' : 
               'Processing document and generating audio...'}
            </p>
            <p className="progress-note">
              This may take 2-5 minutes depending on file size
            </p>
          </div>
        )}
      </div>

      {/* Current Result */}
      {result && (
        <div className="result-section">
          <h3>Generated Podcast</h3>
          
          <div className="result-card">
            <div className="result-header">
              <h4>{result.fileName}</h4>
              <span className="result-date">
                {new Date(result.createdAt).toLocaleString()}
              </span>
            </div>
            
            <div className="result-content">
              <div className="content-section">
                <h4>Summary</h4>
                <div className="summary-text">
                  {result.summary}
                </div>
              </div>
              
              <div className="content-section">
                <h4>Podcast Script</h4>
                <div className="script-container">
                  <pre>{result.podcastScript}</pre>
                </div>
              </div>
              
              <div className="content-section">
                <h4>Audio Preview</h4>
                <div className="audio-container">
                  <audio controls className="audio-player">
                    <source src={result.audioPath} type="audio/mpeg" />
                    Your browser does not support the audio element.
                  </audio>
                  <div className="audio-actions">
                    <a 
                      href={result.audioPath} 
                      download={`podcast-${result.fileName}.mp3`}
                      className="download-audio-btn"
                    >
                      Download MP3
                    </a>
                  </div>
                </div>
              </div>
              
              <div className="file-links">
                <a href={result.fileUrl} target="_blank" rel="noopener noreferrer" className="file-link">
                  📄 View Original File in Firebase
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Previous Podcasts */}
      <div className="history-section">
        <h3>Previous Podcasts ({podcasts.length})</h3>
        {podcasts.length === 0 ? (
          <div className="no-podcasts">
            <p>No podcasts generated yet. Upload a document to get started!</p>
          </div>
        ) : (
          <div className="podcasts-grid">
            {podcasts.map((podcast) => (
              <div key={podcast.id} className="podcast-card">
                <div className="card-header">
                  <h4>{podcast.fileName}</h4>
                  <span className="card-date">
                    {new Date(podcast.createdAt).toLocaleDateString()}
                  </span>
                </div>
                
                <div className="preview-section">
                  <p><strong>Summary:</strong> {podcast.summary?.substring(0, 150)}...</p>
                </div>
                
                <div className="audio-preview">
                  <audio controls className="small-audio-player">
                    <source src={podcast.audioPath} type="audio/mpeg" />
                  </audio>
                </div>
                
                <div className="actions">
                  <button 
                    onClick={() => setResult(podcast)}
                    className="view-btn"
                  >
                    View Full
                  </button>
                  <a 
                    href={podcast.fileUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="download-btn"
                  >
                    Original File
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PodcastGenerator;