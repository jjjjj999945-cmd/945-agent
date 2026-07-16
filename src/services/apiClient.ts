import { httpApi } from "./httpApi";
import { api as mockApi } from "./mockApi";

const apiMode = import.meta.env.VITE_945_API_MODE ?? "mock";

export const api = apiMode === "http" ? httpApi : mockApi;
