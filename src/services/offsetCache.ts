// Offset cache management - persistent storage per track

import { invoke } from '@tauri-apps/api/core';
import { TrackInfo } from '../types';

export interface OffsetCacheEntry {
  global_offset: number;
  anchor_points?: Record<number, number>; // timestamp -> offset
  last_updated: string;
  track_id: string;
  track_name: string;
  artist_name: string;
}

export interface OffsetCache {
  [trackId: string]: OffsetCacheEntry;
}

class OffsetCacheService {
  private cache: OffsetCache = {};
  private initialized = false;

  // Generate unique track ID
  private getTrackId(track: TrackInfo): string {
    return `${track.artist}_${track.name}`.toLowerCase().replace(/[^a-z0-9]/g, '_');
  }

  // Initialize cache from storage
  async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      const savedCache = await invoke<OffsetCache>('load_offset_cache');
      this.cache = savedCache || {};
      this.initialized = true;
      console.log('📦 Offset cache loaded:', Object.keys(this.cache).length, 'entries');
    } catch (error) {
      console.error('Failed to load offset cache:', error);
      this.cache = {};
      this.initialized = true;
    }
  }

  // Save cache to storage
  private async saveCache(): Promise<void> {
    try {
      await invoke('save_offset_cache', { cache: this.cache });
    } catch (error) {
      console.error('Failed to save offset cache:', error);
    }
  }

  // Get saved offset for a track
  async getOffset(track: TrackInfo): Promise<number> {
    await this.initialize();
    
    const trackId = this.getTrackId(track);
    const entry = this.cache[trackId];
    
    if (entry) {
      console.log(`📦 Loaded offset for "${track.name}": ${entry.global_offset}ms`);
      return entry.global_offset;
    }
    
    return 0; // Default offset
  }

  // Save offset for a track
  async setOffset(track: TrackInfo, offset: number): Promise<void> {
    await this.initialize();
    
    const trackId = this.getTrackId(track);
    
    this.cache[trackId] = {
      global_offset: offset,
      last_updated: new Date().toISOString(),
      track_id: trackId,
      track_name: track.name,
      artist_name: track.artist
    };

    console.log(`📦 Saved offset for "${track.name}": ${offset}ms`);
    await this.saveCache();
  }

  // Reset offset for a track
  async resetOffset(track: TrackInfo): Promise<void> {
    await this.initialize();
    
    const trackId = this.getTrackId(track);
    
    if (this.cache[trackId]) {
      this.cache[trackId].global_offset = 0;
      this.cache[trackId].last_updated = new Date().toISOString();
      
      console.log(`📦 Reset offset for "${track.name}"`);
      await this.saveCache();
    }
  }

  // Get anchor point offset for specific timestamp
  async getAnchorOffset(track: TrackInfo, timestamp: number): Promise<number | null> {
    await this.initialize();
    
    const trackId = this.getTrackId(track);
    const entry = this.cache[trackId];
    
    if (entry?.anchor_points) {
      // Find closest anchor point
      const anchors = Object.entries(entry.anchor_points)
        .map(([ts, offset]) => ({ timestamp: parseInt(ts), offset }))
        .sort((a, b) => Math.abs(timestamp - a.timestamp) - Math.abs(timestamp - b.timestamp));
      
      if (anchors.length > 0) {
        const closest = anchors[0];
        // Only use anchor if within 30 seconds
        if (Math.abs(timestamp - closest.timestamp) <= 30000) {
          return closest.offset;
        }
      }
    }
    
    return null; // No suitable anchor point
  }

  // Set anchor point offset for specific timestamp
  async setAnchorOffset(track: TrackInfo, timestamp: number, offset: number): Promise<void> {
    await this.initialize();
    
    const trackId = this.getTrackId(track);
    
    if (!this.cache[trackId]) {
      this.cache[trackId] = {
        global_offset: 0,
        last_updated: new Date().toISOString(),
        track_id: trackId,
        track_name: track.name,
        artist_name: track.artist
      };
    }

    if (!this.cache[trackId].anchor_points) {
      this.cache[trackId].anchor_points = {};
    }

    this.cache[trackId].anchor_points![timestamp] = offset;
    this.cache[trackId].last_updated = new Date().toISOString();

    console.log(`📦 Saved anchor offset for "${track.name}" at ${timestamp}ms: ${offset}ms`);
    await this.saveCache();
  }

  // Clear all cache
  async clearCache(): Promise<void> {
    this.cache = {};
    await this.saveCache();
    console.log('📦 Offset cache cleared');
  }

  // Get cache statistics
  getCacheStats(): { totalTracks: number; totalAnchors: number } {
    const totalTracks = Object.keys(this.cache).length;
    const totalAnchors = Object.values(this.cache)
      .reduce((sum, entry) => sum + (Object.keys(entry.anchor_points || {}).length), 0);
    
    return { totalTracks, totalAnchors };
  }
}

// Export singleton instance
export const offsetCache = new OffsetCacheService();
