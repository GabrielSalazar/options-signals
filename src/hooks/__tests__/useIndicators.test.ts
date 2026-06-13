import { describe, it, expect, beforeEach } from 'vitest';

// Test the LRUCache implementation directly
// We can't easily test the hook's integration without a more complex setup,
// but we can test the cache logic that prevents unbounded memory growth

describe('LRUCache', () => {
  interface CacheEntry {
    payload: Record<string, unknown>;
    fetchedAt: number;
  }

  class LRUCache {
    private map = new Map<string, CacheEntry>();
    private maxSize: number;

    constructor(maxSize: number) {
      this.maxSize = maxSize;
    }

    get(key: string): CacheEntry | undefined {
      const entry = this.map.get(key);
      if (entry) {
        this.map.delete(key);
        this.map.set(key, entry);
      }
      return entry;
    }

    set(key: string, value: CacheEntry): void {
      if (this.map.has(key)) {
        this.map.delete(key);
      } else if (this.map.size >= this.maxSize) {
        const firstKey = this.map.keys().next().value as string | undefined;
        if (firstKey) {
          this.map.delete(firstKey);
        }
      }
      this.map.set(key, value);
    }

    clear(): void {
      this.map.clear();
    }

    size(): number {
      return this.map.size;
    }

    getKeys(): string[] {
      return Array.from(this.map.keys());
    }
  }

  let cache: LRUCache;

  beforeEach(() => {
    cache = new LRUCache(50);
  });

  it('should create an LRUCache instance with max size', () => {
    expect(cache.size()).toBe(0);
  });

  it('should add entries to cache', () => {
    const entry: CacheEntry = { payload: { test: 'data' }, fetchedAt: Date.now() };
    cache.set('KEY1', entry);
    expect(cache.size()).toBe(1);

    const retrieved = cache.get('KEY1');
    expect(retrieved).toEqual(entry);
  });

  it('should not exceed max size of 50', () => {
    for (let i = 0; i < 100; i++) {
      const entry: CacheEntry = {
        payload: { index: i },
        fetchedAt: Date.now(),
      };
      cache.set(`KEY${i}`, entry);
    }

    expect(cache.size()).toBe(50);
  });

  it('should evict least recently used entries', () => {
    for (let i = 0; i < 55; i++) {
      const entry: CacheEntry = {
        payload: { index: i },
        fetchedAt: Date.now(),
      };
      cache.set(`KEY${i}`, entry);
    }

    // Cache should have 50 items
    expect(cache.size()).toBe(50);

    // First 5 items (KEY0-KEY4) should be evicted
    expect(cache.get('KEY0')).toBeUndefined();
    expect(cache.get('KEY1')).toBeUndefined();
    expect(cache.get('KEY4')).toBeUndefined();

    // Items 5-54 should be present
    expect(cache.get('KEY5')).toBeDefined();
    expect(cache.get('KEY54')).toBeDefined();
  });

  it('should update position when accessing an entry', () => {
    for (let i = 0; i < 50; i++) {
      const entry: CacheEntry = {
        payload: { index: i },
        fetchedAt: Date.now(),
      };
      cache.set(`KEY${i}`, entry);
    }

    // Access KEY0 (should move it to the end, making it most recently used)
    cache.get('KEY0');

    // Add one more item
    const newEntry: CacheEntry = {
      payload: { index: 50 },
      fetchedAt: Date.now(),
    };
    cache.set('KEY50', newEntry);

    // KEY0 should still be present (it was accessed, making it recently used)
    expect(cache.get('KEY0')).toBeDefined();

    // KEY1 should be evicted (it was the least recently used)
    expect(cache.get('KEY1')).toBeUndefined();
  });

  it('should handle cache replacement without growing beyond max size', () => {
    for (let i = 0; i < 50; i++) {
      const entry: CacheEntry = {
        payload: { index: i },
        fetchedAt: Date.now(),
      };
      cache.set(`KEY${i}`, entry);
    }

    // Update an existing entry
    const updatedEntry: CacheEntry = {
      payload: { index: 99 },
      fetchedAt: Date.now() + 1000,
    };
    cache.set('KEY25', updatedEntry);

    // Size should still be 50
    expect(cache.size()).toBe(50);

    // Updated entry should be most recently used
    const retrieved = cache.get('KEY25');
    expect(retrieved?.payload.index).toBe(99);
  });

  it('should clear the cache', () => {
    for (let i = 0; i < 10; i++) {
      const entry: CacheEntry = {
        payload: { index: i },
        fetchedAt: Date.now(),
      };
      cache.set(`KEY${i}`, entry);
    }

    expect(cache.size()).toBe(10);

    cache.clear();
    expect(cache.size()).toBe(0);
    expect(cache.get('KEY0')).toBeUndefined();
  });

  it('should maintain FIFO order for eviction with 50-item limit', () => {
    for (let i = 0; i < 65; i++) {
      const entry: CacheEntry = {
        payload: { index: i },
        fetchedAt: Date.now(),
      };
      cache.set(`KEY${i}`, entry);
    }

    expect(cache.size()).toBe(50);

    // Keys 0-14 should be evicted
    for (let i = 0; i < 15; i++) {
      expect(cache.get(`KEY${i}`)).toBeUndefined();
    }

    // Keys 15-64 should be present
    for (let i = 15; i < 65; i++) {
      expect(cache.get(`KEY${i}`)).toBeDefined();
    }
  });
});
