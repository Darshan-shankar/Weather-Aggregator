import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { WeatherDashboard } from "@/components/WeatherDashboard";
import * as api from "@/lib/api";
import type { WeatherReading } from "@/lib/api";

jest.mock("@/lib/api", () => {
  const actual = jest.requireActual("@/lib/api");
  return { ...actual, fetchWeather: jest.fn(), listReadings: jest.fn() };
});

const fetchWeather = api.fetchWeather as jest.MockedFunction<typeof api.fetchWeather>;
const listReadings = api.listReadings as jest.MockedFunction<typeof api.listReadings>;

function reading(overrides: Partial<WeatherReading> = {}): WeatherReading {
  return {
    id: "r1",
    city: "Bangalore",
    country: "India",
    latitude: 12.97,
    longitude: 77.59,
    timezone: "Asia/Kolkata",
    temperature: 22.4,
    temperature_unit: "celsius",
    wind_speed: 14.2,
    wind_speed_unit: "kmh",
    humidity: 65,
    weather_code: 3,
    weather_description: "Overcast",
    observed_at: "2026-11-04T10:00:00Z",
    fetched_at: "2026-11-04T10:05:00Z",
    ...overrides,
  };
}

beforeEach(() => jest.resetAllMocks());

test("entering a city and fetching shows the stored readings, newest first", async () => {
  const user = userEvent.setup();
  const newest = reading({ id: "r2", temperature: 12.5, weather_description: "Rain: slight" });
  const oldest = reading({ id: "r1", temperature: 10 });
  fetchWeather.mockResolvedValue({ reading: newest, cached: false });
  listReadings.mockResolvedValue([newest, oldest]);
  render(<WeatherDashboard />);

  await user.type(screen.getByLabelText("City"), "Bangalore");
  await user.click(screen.getByRole("button", { name: "Fetch weather" }));

  expect(fetchWeather).toHaveBeenCalledWith("Bangalore");
  expect(listReadings).toHaveBeenCalledWith("Bangalore");
  const rows = within(await screen.findByRole("table")).getAllByRole("row").slice(1);
  expect(rows).toHaveLength(2);
  expect(within(rows[0]).getByText("12.5 °C")).toBeInTheDocument();
  expect(within(rows[0]).getByText("Rain: slight")).toBeInTheDocument();
  expect(within(rows[1]).getByText("10.0 °C")).toBeInTheDocument();
});

test("the fetch button is disabled until a city is entered", async () => {
  const user = userEvent.setup();
  render(<WeatherDashboard />);
  const button = screen.getByRole("button", { name: "Fetch weather" });

  expect(button).toBeDisabled();
  await user.type(screen.getByLabelText("City"), "  ");
  expect(button).toBeDisabled();
  await user.type(screen.getByLabelText("City"), "Oslo");
  expect(button).toBeEnabled();
});

test("an unknown city is reported as an error", async () => {
  const user = userEvent.setup();
  fetchWeather.mockRejectedValue(new api.ApiError(404, "City not found: 'Atlantis'"));
  render(<WeatherDashboard />);

  await user.type(screen.getByLabelText("City"), "Atlantis");
  await user.click(screen.getByRole("button", { name: "Fetch weather" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(/couldn’t find a city called “Atlantis”/);
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});

test("a provider outage is reported in friendly words", async () => {
  const user = userEvent.setup();
  fetchWeather.mockRejectedValue(new api.ApiError(502, "Weather provider unavailable"));
  render(<WeatherDashboard />);

  await user.type(screen.getByLabelText("City"), "Oslo");
  await user.click(screen.getByRole("button", { name: "Fetch weather" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(/not responding/i);
});

test("a reused (cached) reading is explained to the user", async () => {
  const user = userEvent.setup();
  fetchWeather.mockResolvedValue({ reading: reading(), cached: true });
  listReadings.mockResolvedValue([reading()]);
  render(<WeatherDashboard />);

  await user.type(screen.getByLabelText("City"), "Bangalore");
  await user.click(screen.getByRole("button", { name: "Fetch weather" }));

  expect(await screen.findByText(/was reused/i)).toBeInTheDocument();
});

test("showing stored readings does not trigger a new fetch", async () => {
  const user = userEvent.setup();
  listReadings.mockResolvedValue([]);
  render(<WeatherDashboard />);

  await user.type(screen.getByLabelText("City"), "Bangalore");
  await user.click(screen.getByRole("button", { name: "Show stored readings" }));

  expect(fetchWeather).not.toHaveBeenCalled();
  expect(await screen.findByText(/No readings stored/)).toBeInTheDocument();
});
