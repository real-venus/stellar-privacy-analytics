import { APIKeyManager } from "../APIKeyManager";

jest.mock("../../utils/logger");

describe("APIKeyManager", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  describe("listKeys", () => {
    it("returns deep-cloned keys so callers cannot mutate internal state", async () => {
      const manager = new APIKeyManager();
      const { key: apiKey, keyInfo } = await manager.createKey({
        name: "Analytics Reader",
        permissions: ["read"],
        rateLimit: {
          requestsPerMinute: 10,
          requestsPerHour: 100,
          requestsPerDay: 1000,
        },
        restrictions: {
          allowedIPs: ["10.0.0.1"],
          allowedOrigins: ["https://analytics.example.com"],
          allowedServices: ["analytics"],
        },
        metadata: {
          owner: "security-team",
          department: "security",
          purpose: "regression-test",
        },
      });

      const listedKeys = await manager.listKeys({ owner: "security-team" });
      const listedKey = listedKeys[0];

      listedKeys.pop();
      listedKey.permissions.push("admin");
      listedKey.restrictions.allowedIPs.push("0.0.0.0/0");
      listedKey.restrictions.allowedOrigins.push("*");
      listedKey.restrictions.allowedServices.push("admin-console");
      listedKey.metadata.isActive = false;
      listedKey.metadata.owner = "attacker";
      listedKey.rateLimit!.requestsPerMinute = 9999;

      const freshKeys = await manager.listKeys({ owner: "security-team" });
      const freshKey = freshKeys.find((key) => key.id === keyInfo.id);

      expect(freshKey).toBeDefined();
      expect(freshKeys).toHaveLength(1);
      expect(freshKey!.permissions).toEqual(["read"]);
      expect(freshKey!.restrictions.allowedIPs).toEqual(["10.0.0.1"]);
      expect(freshKey!.restrictions.allowedOrigins).toEqual([
        "https://analytics.example.com",
      ]);
      expect(freshKey!.restrictions.allowedServices).toEqual(["analytics"]);
      expect(freshKey!.metadata.isActive).toBe(true);
      expect(freshKey!.metadata.owner).toBe("security-team");
      expect(freshKey!.rateLimit!.requestsPerMinute).toBe(10);

      await expect(
        manager.validateKey(apiKey, {
          ipAddress: "10.0.0.1",
          origin: "https://analytics.example.com",
          service: "analytics",
        }),
      ).resolves.toMatchObject({ valid: true });
    });
  });
});
