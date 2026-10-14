import { afterEach, describe, expect, it, vi } from "vitest";

describe("driverFetch 401 recovery", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("refreshes the Clerk token once and replays the request", async () => {
    const getToken = vi.fn().mockResolvedValue("fresh");
    vi.stubGlobal("window", {
      Clerk: { session: { getToken } },
      location: { pathname: "/account", href: "" },
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "invalid_driver_token" }), { status: 401 })
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "d1" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { accountApi } = await import("./api");
    await expect(accountApi.profile()).resolves.toEqual({ id: "d1" });
    expect(getToken).toHaveBeenCalledWith({ skipCache: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("surfaces field validation errors as JSON", async () => {
    vi.stubGlobal("window", { location: { pathname: "/account", href: "" } });
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ detail: { field: "address.postal_code", code: "invalid" } }),
            { status: 422 }
          )
        )
    );
    const { accountApi } = await import("./api");
    await expect(accountApi.updateProfile({})).rejects.toThrow(
      '{"field":"address.postal_code","code":"invalid"}'
    );
  });
});
