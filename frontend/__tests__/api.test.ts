import { ApiError, fetchWeather, listReadings } from "@/lib/api";

// jsdom has no global Response, so use a minimal stand-in.
const json = (body: unknown, status = 200) =>
  Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  });

beforeEach(() => {
  global.fetch = jest.fn();
});

test("fetchWeather POSTs the encoded city and flags 201 as a new reading", async () => {
  (global.fetch as jest.Mock).mockReturnValue(json({ id: "1" }, 201));

  const outcome = await fetchWeather("São Paulo");

  expect(global.fetch).toHaveBeenCalledWith("/api/weather/fetch?city=S%C3%A3o%20Paulo", {
    method: "POST",
  });
  expect(outcome.cached).toBe(false);
});

test("fetchWeather flags HTTP 200 as a cached reading", async () => {
  (global.fetch as jest.Mock).mockReturnValue(json({ id: "1" }, 200));

  expect((await fetchWeather("Oslo")).cached).toBe(true);
});

test("errors carry the status and the backend's detail message", async () => {
  (global.fetch as jest.Mock).mockReturnValue(json({ detail: "City not found" }, 404));

  await expect(fetchWeather("Atlantis")).rejects.toMatchObject({
    status: 404,
    message: "City not found",
  });
  await expect(fetchWeather("Atlantis")).rejects.toBeInstanceOf(ApiError);
});

test("listReadings returns the parsed list", async () => {
  (global.fetch as jest.Mock).mockReturnValue(json([{ id: "1" }, { id: "2" }]));

  expect(await listReadings("Oslo")).toHaveLength(2);
  expect(global.fetch).toHaveBeenCalledWith("/api/weather/Oslo");
});
