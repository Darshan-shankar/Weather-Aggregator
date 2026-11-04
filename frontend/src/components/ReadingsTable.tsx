import type { WeatherReading } from "@/lib/api";

export function formatUtc(iso: string): string {
  return `${new Date(iso).toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

export function ReadingsTable({ readings }: { readings: WeatherReading[] }) {
  return (
    <table>
      <caption>
        {readings[0].city}, {readings[0].country}: {readings.length}{" "}
        {readings.length === 1 ? "reading" : "readings"}, newest first
      </caption>
      <thead>
        <tr>
          <th scope="col">Fetched</th>
          <th scope="col">Observed</th>
          <th scope="col">Conditions</th>
          <th scope="col">Temperature</th>
          <th scope="col">Wind</th>
          <th scope="col">Humidity</th>
        </tr>
      </thead>
      <tbody>
        {readings.map((r) => (
          <tr key={r.id}>
            <td>{formatUtc(r.fetched_at)}</td>
            <td>{formatUtc(r.observed_at)}</td>
            <td>{r.weather_description}</td>
            <td>{r.temperature.toFixed(1)} °C</td>
            <td>{r.wind_speed.toFixed(1)} km/h</td>
            <td>{r.humidity === null ? "n/a" : `${r.humidity}%`}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
