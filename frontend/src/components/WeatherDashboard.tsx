"use client";

import { useEffect, useState } from "react";

import {
  ApiError,
  fetchWeather,
  listReadings,
  type WeatherReading,
} from "@/lib/api";
import { CityForm } from "./CityForm";
import { ReadingsTable } from "./ReadingsTable";

function describeError(error: unknown, city: string): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return `We couldn’t find a city called “${city}”.`;
    if (error.status === 502)
      return "The weather provider is not responding right now. Please try again shortly.";
    return error.message;
  }
  return "Could not reach the server. Check your connection and try again.";
}

export function WeatherDashboard() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [readings, setReadings] = useState<WeatherReading[] | null>(null);
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  async function run(city: string, action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
    } catch (e) {
      setError(describeError(e, city));
    } finally {
      setBusy(false);
    }
  }

  const handleFetch = (city: string) =>
    run(city, async () => {
      const { cached } = await fetchWeather(city);
      setReadings(await listReadings(city));
      if (cached)
        setNotice("A recent reading was already stored, so it was reused.");
    });

  const handleShowHistory = (city: string) =>
    run(city, async () => setReadings(await listReadings(city)));

  return (
    <main>
      <h1>Weather Aggregator</h1>
      <p className="lede">
        Fetch the current conditions for a city and keep a history of every
        reading.
      </p>
      {now && (
        <div className="current-time" aria-label="Current local time and date">
          <time dateTime={now.toISOString()}>
            <span>{now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
            <small>
              {now.toLocaleDateString([], {
                weekday: "long",
                month: "long",
                day: "numeric",
              })}
            </small>
          </time>
        </div>
      )}
      <CityForm
        busy={busy}
        onFetch={handleFetch}
        onShowHistory={handleShowHistory}
      />
      <div aria-live="polite" aria-busy={busy}>
        {busy && <p>Loading…</p>}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {notice && <p className="notice">{notice}</p>}
      </div>
      {readings !== null &&
        (readings.length === 0 ? (
          <p>No readings stored for this city yet.</p>
        ) : (
          <ReadingsTable readings={readings} />
        ))}
    </main>
  );
}
