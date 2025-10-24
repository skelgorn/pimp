// Multi-source lyrics service with instrumental detection

import { invoke } from '@tauri-apps/api/core';
import { LyricsData, TrackInfo } from '../types';

export interface LyricsSource {
  name: string;
  priority: number;
  getSyncedLyrics: (track: TrackInfo) => Promise<LyricsData | null>;
  detectInstrumental: (track: TrackInfo) => Promise<boolean>;
}

class LyricsService {
  private sources: LyricsSource[] = [];

  // Register lyrics sources in priority order
  constructor() {
    this.registerSources();
  }

  private registerSources() {
    // Priority 1: Musixmatch (best synced lyrics)
    this.sources.push({
      name: 'Musixmatch',
      priority: 1,
      getSyncedLyrics: this.getMusixmatchLyrics.bind(this),
      detectInstrumental: this.detectMusixmatchInstrumental.bind(this)
    });

    // Priority 2: Spotify Lyrics (official when available)
    this.sources.push({
      name: 'Spotify',
      priority: 2,
      getSyncedLyrics: this.getSpotifyLyrics.bind(this),
      detectInstrumental: this.detectSpotifyInstrumental.bind(this)
    });

    // Priority 3: LRCLIB (community)
    this.sources.push({
      name: 'LRCLIB',
      priority: 3,
      getSyncedLyrics: this.getLRCLIBLyrics.bind(this),
      detectInstrumental: this.detectLRCLIBInstrumental.bind(this)
    });

    // Priority 4: Genius (fallback, no sync)
    this.sources.push({
      name: 'Genius',
      priority: 4,
      getSyncedLyrics: this.getGeniusLyrics.bind(this),
      detectInstrumental: this.detectGeniusInstrumental.bind(this)
    });
  }

  // Main method to get lyrics from best available source
  async getLyrics(track: TrackInfo): Promise<LyricsData | null> {
    console.log(`🎵 Searching lyrics for: ${track.artist} - ${track.name}`);

    // First check if track is instrumental
    const isInstrumental = await this.isTrackInstrumental(track);
    if (isInstrumental) {
      console.log('🎼 Track detected as instrumental');
      return {
        blocks: [],
        quality: 'Instrumental'
      };
    }

    // Try each source in priority order
    for (const source of this.sources.sort((a, b) => a.priority - b.priority)) {
      try {
        console.log(`📡 Trying ${source.name}...`);
        const lyrics = await source.getSyncedLyrics(track);
        
        if (lyrics && lyrics.blocks.length > 0) {
          console.log(`✅ Found lyrics from ${source.name}: ${lyrics.blocks.length} blocks, quality: ${lyrics.quality}`);
          return lyrics;
        }
      } catch (error) {
        console.warn(`❌ ${source.name} failed:`, error);
      }
    }

    console.log('❌ No lyrics found from any source');
    return null;
  }

  // Check if track is instrumental using multiple methods
  private async isTrackInstrumental(track: TrackInfo): Promise<boolean> {
    // Try each source's instrumental detection
    for (const source of this.sources) {
      try {
        const isInstrumental = await source.detectInstrumental(track);
        if (isInstrumental) {
          console.log(`🎼 ${source.name} detected instrumental`);
          return true;
        }
      } catch (error) {
        // Continue to next source
      }
    }

    return false;
  }

  // Musixmatch implementation
  private async getMusixmatchLyrics(track: TrackInfo): Promise<LyricsData | null> {
    try {
      return await invoke<LyricsData | null>('get_musixmatch_lyrics', {
        artist: track.artist,
        title: track.name,
        duration: track.duration_ms
      });
    } catch (error) {
      console.error('Musixmatch error:', error);
      return null;
    }
  }

  private async detectMusixmatchInstrumental(track: TrackInfo): Promise<boolean> {
    try {
      return await invoke<boolean>('is_musixmatch_instrumental', {
        artist: track.artist,
        title: track.name
      });
    } catch (error) {
      return false;
    }
  }

  // Spotify implementation
  private async getSpotifyLyrics(track: TrackInfo): Promise<LyricsData | null> {
    try {
      return await invoke<LyricsData | null>('get_spotify_lyrics', {
        track_id: track.id || '',
        artist: track.artist,
        title: track.name
      });
    } catch (error) {
      console.error('Spotify lyrics error:', error);
      return null;
    }
  }

  private async detectSpotifyInstrumental(track: TrackInfo): Promise<boolean> {
    try {
      // Use Spotify's audio features
      const features = await invoke<any>('get_spotify_audio_features', {
        track_id: track.id || ''
      });
      
      return features && 
             features.speechiness < 0.1 && 
             features.instrumentalness > 0.7;
    } catch (error) {
      return false;
    }
  }

  // LRCLIB implementation
  private async getLRCLIBLyrics(track: TrackInfo): Promise<LyricsData | null> {
    try {
      return await invoke<LyricsData | null>('get_lrclib_lyrics', {
        artist: track.artist,
        title: track.name,
        duration: Math.floor(track.duration_ms / 1000)
      });
    } catch (error) {
      console.error('LRCLIB error:', error);
      return null;
    }
  }

  private async detectLRCLIBInstrumental(_track: TrackInfo): Promise<boolean> {
    // LRCLIB doesn't have explicit instrumental detection
    return false;
  }

  // Genius implementation (fallback)
  private async getGeniusLyrics(track: TrackInfo): Promise<LyricsData | null> {
    try {
      const lyricsText = await invoke<string | null>('get_genius_lyrics', {
        artist: track.artist,
        title: track.name
      });

      if (!lyricsText) return null;

      // Convert plain text to basic blocks (no sync)
      const lines = lyricsText.split('\n').filter(line => line.trim());
      const blocks = lines.map((text, index) => ({
        start: index * 3000, // Fake timing: 3 seconds per line
        end: (index + 1) * 3000,
        text: text.trim()
      }));

      return {
        blocks,
        quality: 'Unsynced'
      };
    } catch (error) {
      console.error('Genius error:', error);
      return null;
    }
  }

  private async detectGeniusInstrumental(track: TrackInfo): Promise<boolean> {
    try {
      const metadata = await invoke<any>('get_genius_metadata', {
        artist: track.artist,
        title: track.name
      });
      
      // Check if explicitly marked as instrumental
      return metadata && metadata.instrumental === true;
    } catch (error) {
      return false;
    }
  }

  // Utility: Check if lyrics content is likely instrumental (unused for now)
  /*
  private isLyricsContentInstrumental(lyrics: LyricsData): boolean {
    if (!lyrics.blocks || lyrics.blocks.length === 0) return true;

    const totalText = lyrics.blocks.map(b => b.text).join(' ');
    
    // Very short content
    if (totalText.length < 50) return true;

    // Only humming/vocalization
    const hummingPattern = /^[\s\w]*(?:hmm|ahh|ohh|la|na|da|mm|ah|oh|yeah|hey|ho|ha|ooh|aah|eh|uh|huh|wow|whoa|shh|tsk|pfft|brr|grr|psst|tut|bah|blah|duh|gah|hah|meh|nah|pah|psh|rah|tch|tsk|ugh|yah|yep|yup|zip|bam|pow|zap|pop|bop|bip|beep|buzz|fizz|hiss|ping|ring|ting|zing|boom|bang|clap|snap|tap|thud|thump|whack|smack|crack|crash|splash|swoosh|swish|whoosh|zoom|vroom|screech|squeak|squeal|chirp|tweet|peep|cheep|meow|woof|moo|oink|neigh|roar|growl|howl|bark|yelp|whine|purr|hiss|snarl|grunt|snort|wheeze|gasp|sigh|yawn|hiccup|burp|sneeze|cough|chuckle|giggle|laugh|sob|cry|wail|scream|shout|whisper|mumble|mutter|babble|jabber|chatter|prattle|ramble|rant|rave|gush|blurt|stutter|stammer|slur|drawl|drone|monotone|sing|hum|whistle|trill|warble|croon|belt|belt out|belt it out|belt it|belt one out|belt them out|belt 'em out|belt 'em|belt em out|belt em)[\s\w]*$/i;
    
    return hummingPattern.test(totalText);
  }
  */
}

// Export singleton instance
export const lyricsService = new LyricsService();
