// src/lib/api.ts
import axios from "axios";

// This is the base URL of our FastAPI server
const API_URL = "http://127.0.0.1:8000";

// Create the main axios instance
export const api = axios.create({
  baseURL: API_URL,
});

// This is a powerful feature called an "interceptor".
// It will automatically add the 'Authorization' header
// to every single request we make using this 'api' instance,
// as long as a token exists in localStorage.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("aegis_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// We'll also create a separate, un-authenticated
// instance for things like login/signup
export const authApi = axios.create({
  baseURL: API_URL,
});
