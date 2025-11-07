// App.js
import React from 'react';
import PodcastGenerator from './PodcastGenerator';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>AI Podcast Generator</h1>
        <p>Transform your documents into engaging podcast conversations</p>
      </header>
      <main>
        <PodcastGenerator />
      </main>
    </div>
  );
}

export default App;