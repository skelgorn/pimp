// lyrics.rs - LRCLIB integration and lyrics fetching

use crate::types::{LyricsData, LyricsBlock, LyricsQuality, Result, AppError};
use crate::config::AppConfig;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use chrono::Utc;
use tracing::{info, warn, error, debug};
use std::time::Duration;
use regex::Regex;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct LrclibSearchResult {
    id: u64,
    name: String,
    #[serde(rename = "trackName")]
    track_name: String,
    #[serde(rename = "artistName")]
    artist_name: String,
    #[serde(rename = "albumName")]
    album_name: String,
    duration: f64,
    instrumental: bool,
    #[serde(rename = "syncedLyrics")]
    synced_lyrics: Option<String>,
    #[serde(rename = "plainLyrics")]
    plain_lyrics: Option<String>,
}

#[derive(Debug)]
pub struct LyricsClient {
    client: Client,
    base_url: String,
}

impl LyricsClient {
    pub fn new(config: &AppConfig) -> Self {
        Self {
            client: Client::builder()
                .timeout(Duration::from_secs(10))
                .user_agent("LetrasPIP/1.0")
                .build()
                .expect("Failed to create HTTP client"),
            base_url: config.lyrics.lrclib_base_url.clone(),
        }
    }

    pub async fn search_lyrics(&self, artist: &str, title: &str) -> Result<Option<LyricsData>> {
        info!("Searching lyrics for: {} - {}", artist, title);

        // First try exact search
        if let Ok(Some(lyrics)) = self.search_exact(artist, title).await {
            return Ok(Some(lyrics));
        }

        // Then try fuzzy search
        if let Ok(Some(lyrics)) = self.search_fuzzy(artist, title).await {
            return Ok(Some(lyrics));
        }

        // Check if it's instrumental
        if self.is_likely_instrumental(title) {
            info!("Track appears to be instrumental: {}", title);
            return Ok(Some(LyricsData {
                blocks: Vec::new(),
                source: "detected".to_string(),
                quality: LyricsQuality::Instrumental,
                confidence: 0.9,
                cached_at: Utc::now(),
            }));
        }

        warn!("No lyrics found for: {} - {}", artist, title);
        Err(AppError::LyricsNotFound)
    }

    async fn search_exact(&self, artist: &str, title: &str) -> Result<Option<LyricsData>> {
        let url = format!(
            "{}/search?artist_name={}&track_name={}",
            self.base_url,
            urlencoding::encode(artist),
            urlencoding::encode(title)
        );

        debug!("LRCLIB exact search: {}", url);

        let response = self.client.get(&url).send().await?;

        if !response.status().is_success() {
            warn!("LRCLIB search failed: {}", response.status());
            return Ok(None);
        }

        let results: Vec<LrclibSearchResult> = response.json().await?;

        if let Some(result) = results.first() {
            self.convert_result_to_lyrics_data(result).await
        } else {
            Ok(None)
        }
    }

    async fn search_fuzzy(&self, artist: &str, title: &str) -> Result<Option<LyricsData>> {
        // Clean up search terms for better matching
        let clean_artist = self.clean_search_term(artist);
        let clean_title = self.clean_search_term(title);

        let url = format!(
            "{}/search?q={} {}",
            self.base_url,
            urlencoding::encode(&clean_artist),
            urlencoding::encode(&clean_title)
        );

        debug!("LRCLIB fuzzy search: {}", url);

        let response = self.client.get(&url).send().await?;

        if !response.status().is_success() {
            return Ok(None);
        }

        let results: Vec<LrclibSearchResult> = response.json().await?;

        // Find best match
        let best_match = results.iter()
            .filter(|result| !result.instrumental)
            .max_by_key(|result| {
                self.calculate_similarity_score(&result.artist_name, &result.track_name, artist, title)
            });

        if let Some(result) = best_match {
            self.convert_result_to_lyrics_data(result).await
        } else {
            Ok(None)
        }
    }

    async fn convert_result_to_lyrics_data(&self, result: &LrclibSearchResult) -> Result<Option<LyricsData>> {
        if result.instrumental {
            return Ok(Some(LyricsData {
                blocks: Vec::new(),
                source: "lrclib".to_string(),
                quality: LyricsQuality::Instrumental,
                confidence: 1.0,
                cached_at: Utc::now(),
            }));
        }

        if let Some(ref synced_lyrics) = result.synced_lyrics {
            if !synced_lyrics.trim().is_empty() {
                let blocks = self.parse_lrc(synced_lyrics)?;
                if !blocks.is_empty() {
                    info!("Found {} synced lyrics blocks", blocks.len());
                    return Ok(Some(LyricsData {
                        blocks,
                        source: "lrclib".to_string(),
                        quality: LyricsQuality::High,
                        confidence: 0.95,
                        cached_at: Utc::now(),
                    }));
                }
            }
        }

        if let Some(ref plain_lyrics) = result.plain_lyrics {
            if !plain_lyrics.trim().is_empty() {
                // Convert plain lyrics to blocks (less useful but better than nothing)
                let blocks = self.plain_lyrics_to_blocks(plain_lyrics);
                info!("Found plain lyrics, converted to {} blocks", blocks.len());
                return Ok(Some(LyricsData {
                    blocks,
                    source: "lrclib".to_string(),
                    quality: LyricsQuality::Low,
                    confidence: 0.7,
                    cached_at: Utc::now(),
                }));
            }
        }

        Ok(None)
    }

    fn parse_lrc(&self, lrc_content: &str) -> Result<Vec<LyricsBlock>> {
        let lrc_regex = Regex::new(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")
            .map_err(|e| AppError::Config(format!("Regex error: {}", e)))?;

        let mut blocks = Vec::new();
        let mut times_and_texts = Vec::new();

        // Parse all time markers and texts
        for line in lrc_content.lines() {
            if let Some(captures) = lrc_regex.captures(line) {
                let minutes: u64 = captures[1].parse().unwrap_or(0);
                let seconds: u64 = captures[2].parse().unwrap_or(0);
                let mut centiseconds: u64 = captures[3].parse().unwrap_or(0);

                // Handle different centisecond formats (2 or 3 digits)
                if captures[3].len() == 2 {
                    centiseconds *= 10;
                }

                let time_ms = minutes * 60000 + seconds * 1000 + centiseconds;
                let text = captures[4].trim().to_string();

                if !text.is_empty() && !self.is_metadata_line(&text) {
                    times_and_texts.push((time_ms, text));
                }
            }
        }

        // Sort by time
        times_and_texts.sort_by_key(|(time, _)| *time);

        // Create blocks with start and end times
        for i in 0..times_and_texts.len() {
            let (start_time, text) = &times_and_texts[i];
            let end_time = if i + 1 < times_and_texts.len() {
                times_and_texts[i + 1].0
            } else {
                start_time + 5000 // Default 5 seconds for last line
            };

            // Ensure minimum duration of 2 seconds
            let end_time = std::cmp::max(end_time, start_time + 2000);

            blocks.push(LyricsBlock {
                start: *start_time,
                end: end_time,
                text: text.clone(),
            });
        }

        debug!("Parsed {} LRC blocks", blocks.len());
        Ok(blocks)
    }

    fn plain_lyrics_to_blocks(&self, plain_lyrics: &str) -> Vec<LyricsBlock> {
        let lines: Vec<&str> = plain_lyrics
            .lines()
            .map(|line| line.trim())
            .filter(|line| !line.is_empty() && !self.is_metadata_line(line))
            .collect();

        let mut blocks = Vec::new();
        let line_duration = 4000; // 4 seconds per line

        for (i, line) in lines.iter().enumerate() {
            let start_time = (i as u64) * line_duration;
            let end_time = start_time + line_duration;

            blocks.push(LyricsBlock {
                start: start_time,
                end: end_time,
                text: line.to_string(),
            });
        }

        blocks
    }

    fn is_metadata_line(&self, text: &str) -> bool {
        let metadata_prefixes = [
            "[ar:", "[ti:", "[al:", "[by:", "[offset:",
            "[length:", "[tool:", "[ve:", "[re:",
        ];

        let text_lower = text.to_lowercase();
        metadata_prefixes.iter().any(|prefix| text_lower.starts_with(prefix))
            || text.starts_with('[') && text.ends_with(']')
            || text.is_empty()
    }

    fn clean_search_term(&self, term: &str) -> String {
        // Remove common suffixes and parenthetical content
        let cleaners = [
            r"\s*\([^)]*\)",     // Remove parentheses
            r"\s*\[[^\]]*\]",   // Remove brackets
            r"\s*-\s*remaster.*", // Remove remaster info
            r"\s*-\s*remix.*",    // Remove remix info
            r"\s*feat\..*",       // Remove featuring
            r"\s*ft\..*",         // Remove ft.
        ];

        let mut cleaned = term.to_lowercase();
        for pattern in &cleaners {
            if let Ok(regex) = Regex::new(pattern) {
                cleaned = regex.replace_all(&cleaned, "").to_string();
            }
        }

        cleaned.trim().to_string()
    }

    fn calculate_similarity_score(&self, result_artist: &str, result_title: &str, search_artist: &str, search_title: &str) -> u32 {
        let artist_similarity = self.string_similarity(&result_artist.to_lowercase(), &search_artist.to_lowercase());
        let title_similarity = self.string_similarity(&result_title.to_lowercase(), &search_title.to_lowercase());

        // Weight title similarity more heavily
        ((title_similarity * 0.7 + artist_similarity * 0.3) * 100.0) as u32
    }

    fn string_similarity(&self, s1: &str, s2: &str) -> f32 {
        // Simple Jaccard similarity using character bigrams
        let bigrams1: std::collections::HashSet<String> = s1.chars()
            .collect::<Vec<_>>()
            .windows(2)
            .map(|w| format!("{}{}", w[0], w[1]))
            .collect();

        let bigrams2: std::collections::HashSet<String> = s2.chars()
            .collect::<Vec<_>>()
            .windows(2)
            .map(|w| format!("{}{}", w[0], w[1]))
            .collect();

        let intersection = bigrams1.intersection(&bigrams2).count();
        let union = bigrams1.union(&bigrams2).count();

        if union == 0 {
            0.0
        } else {
            intersection as f32 / union as f32
        }
    }

    fn is_likely_instrumental(&self, title: &str) -> bool {
        let instrumental_keywords = [
            "instrumental", "inst.", "karaoke", "backing track",
            "without vocals", "no vocals", "music only", "interlude",
            "intro", "outro", "theme", "ost", "suite",
        ];

        let title_lower = title.to_lowercase();
        instrumental_keywords.iter().any(|keyword| title_lower.contains(keyword))
    }
}