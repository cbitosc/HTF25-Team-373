// firebase.js
import { initializeApp } from "firebase/app";
import { getStorage, ref, uploadBytes, getDownloadURL } from 'firebase/storage';
import { getFirestore, collection, addDoc, getDocs } from 'firebase/firestore';

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyAdHU9L0MGuusmoBDKycs82-8OpZ4Ghkio",
  authDomain: "podcase-generator.firebaseapp.com",
  projectId: "podcase-generator",
  storageBucket: "podcase-generator.firebasestorage.app",
  messagingSenderId: "777195165565",
  appId: "1:777195165565:web:574ddab8b7d68cf3cf5e14",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Storage
export const storage = getStorage(app);

// Initialize Firestore
export const db = getFirestore(app);

export default app;