import axios from 'axios';

// The base URL defaults to the Vite proxy or the explicit VITE_API_URL env var
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// TODO: add response interceptors for global error handling if needed

export default apiClient;
