import axios from "axios";
import { API_BASE_URL, API_KEY } from "../constants/api";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use((config) => {
  config.headers["X-API-Key"] = API_KEY;
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response?.status, error.response?.data);
    return Promise.reject(error);
  },
);

export default client;
