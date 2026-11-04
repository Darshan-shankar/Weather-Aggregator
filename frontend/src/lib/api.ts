// The UI's single gateway to the backend. Components never call fetch directly.

export type WeatherReading = {
  id: string;
  city: string;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
  temperature: number;
  temperature_unit: string;
  wind_speed: number;
  wind_speed_unit: string;
  humidity: number | null;
  weather_code: number;
  weather_description: string;
  observed_at: string;
  fetched_at: string;
};

export type FetchOutcome = {
  reading: WeatherReading;
  /** true when the backend served a still-fresh stored reading (HTTP 200). */
  cached: boolean;
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Proxied to the FastAPI backend by next.config.mjs
const BASE_URL = "/api";

async function toApiError(response: Response): Promise<ApiError> {
  let message = response.statusText || `Request failed (${response.status})`;
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") message = body.detail;
  } catch {
    /* body was not JSON: keep the status text */
  }
  return new ApiError(response.status, message);
}

export async function fetchWeather(city: string): Promise<FetchOutcome> {
  const response = await fetch(
    `${BASE_URL}/weather/fetch?city=${encodeURIComponent(city)}`,
    { method: "POST" },
  );
  if (!response.ok) throw await toApiError(response);
  return { reading: await response.json(), cached: response.status === 200 };
}

export async function listReadings(city: string): Promise<WeatherReading[]> {
  const response = await fetch(
    `${BASE_URL}/weather/${encodeURIComponent(city)}`,
  );
  if (!response.ok) throw await toApiError(response);
  return response.json();
}
