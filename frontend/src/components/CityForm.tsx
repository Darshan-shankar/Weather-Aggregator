"use client";

import { FormEvent, useState } from "react";

type Props = {
  busy: boolean;
  onFetch: (city: string) => void;
  onShowHistory: (city: string) => void;
};

export function CityForm({ busy, onFetch, onShowHistory }: Props) {
  const [city, setCity] = useState("");
  const trimmed = city.trim();

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (trimmed) onFetch(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="city-form">
      <label htmlFor="city">City</label>
      <input
        id="city"
        name="city"
        value={city}
        onChange={(e) => setCity(e.target.value)}
        placeholder="e.g. Bangalore"
        autoComplete="off"
      />
      <button type="submit" disabled={busy || !trimmed}>
        Fetch weather
      </button>
      <button
        type="button"
        className="secondary"
        disabled={busy || !trimmed}
        onClick={() => onShowHistory(trimmed)}
      >
        Show stored readings
      </button>
    </form>
  );
}
