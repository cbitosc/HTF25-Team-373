import React from 'react';

// This component is purely presentational, displaying the results passed to it.
const ResultsDisplay = ({ result }) => {
    // Safety check: ensure we have results and a valid audio URL before rendering
    if (!result || !result.audio_url) return null;

    // The audioUrl is the permanent public URL returned from the FastAPI backend,
    // which uploaded the file to Firebase Cloud Storage.
    const audioUrl = result.audio_url; 

    return (
        <div className="mt-10 space-y-8">
            <h2 className="text-3xl font-bold text-gray-900 border-b pb-2">Generation Results</h2>

            {/* Audio Player */}
            <div className="bg-indigo-50 p-6 rounded-lg shadow-inner">
                <h3 className="text-xl font-semibold text-indigo-800 mb-3">3. Final Audio Output</h3>
                <audio controls src={audioUrl} className="w-full">
                    Your browser does not support the audio element.
                </audio>
                <p className="text-sm text-indigo-600 mt-2">
                    *The audio is streamed directly from Firebase Storage: <code>{audioUrl}</code>
                </p>
            </div>

            {/* Summary */}
            <div>
                <h3 className="text-xl font-semibold text-gray-700 mb-2">1. AI Summary</h3>
                <p className="text-gray-800 bg-white p-4 rounded-lg border">{result.summary}</p>
            </div>

            {/* Script */}
            <div>
                <h3 className="text-xl font-semibold text-gray-700 mb-2">2. Podcast Script</h3>
                <pre className="text-sm text-gray-800 bg-gray-100 p-4 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">
                    {result.podcast_script}
                </pre>
            </div>
        </div>
    );
};

export default ResultsDisplay;
