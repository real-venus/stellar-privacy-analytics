import { APIKeyManager } from '../APIKeyManager';

describe('APIKeyManager', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('listKeys', () => {
    it('returns deep-cloned keys so callers cannot mutate stored state', async () => {
      const manager = new APIKeyManager();
      const { key, keyInfo } = await manager.createKey({
        name: 'Analytics Read Key',
        permissions: ['read'],
        rateLimit: {
          requestsPerMinute: 10,
          requestsPerHour: 100,
          requestsPerDay: 1000
        },
        restrictions: {
          allowedIPs: ['127.0.0.1'],
          allowedOrigins: ['https://example.com'],
          allowedServices: []
        },
        metadata: {
          owner: 'clone-test-owner',
          department: 'security',
          purpose: 'Verify listKeys clone behavior'
        }
      });

      const listedKeys = await manager.listKeys({ owner: 'clone-test-owner' });
      const listedKey = listedKeys[0];

      listedKey.permissions.push('admin');
      listedKey.metadata.isActive = false;
      listedKey.restrictions.allowedServices.push('admin-service');
      listedKey.rateLimit!.requestsPerDay = 999999;

      const refreshedKeys = await manager.listKeys({ owner: 'clone-test-owner' });
      const refreshedKey = refreshedKeys.find(candidate => candidate.id === keyInfo.id)!;
      const validation = await manager.validateKey(key, {
        ipAddress: '127.0.0.1',
        origin: 'https://example.com',
        service: 'analytics'
      });

      expect(refreshedKey.permissions).toEqual(['read']);
      expect(refreshedKey.metadata.isActive).toBe(true);
      expect(refreshedKey.restrictions.allowedServices).toEqual([]);
      expect(refreshedKey.rateLimit?.requestsPerDay).toBe(1000);
      expect(validation.valid).toBe(true);
    });
  });
});
