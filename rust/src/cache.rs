//! In-memory caching using moka
//!
//! Provides application-level caching for CMS pages, blog content, and pricing data.
//! Blog content rarely changes after publishing, so aggressive TTLs are used.
//! Pricing agreements are cached with 1-hour TTL since they rarely change.

use moka::future::Cache;
use serde::Serialize;
use sqlx::PgPool;
use std::sync::Arc;
use std::time::Duration;
use tokio::time::interval;
use tracing::{info, warn};

use crate::db::queries;
use crate::models::{BlogPostSummary, CmsSettings, ParsedPage};
use crate::pricing::models::{Agreement, ContentType};

/// Application cache holding parsed pages, blog listings, and pricing data
#[derive(Clone)]
pub struct AppCache {
    /// CMS pages (slug -> ParsedPage)
    pub pages: Cache<String, Arc<ParsedPage>>,
    /// Blog posts (slug -> ParsedPage)
    pub blog_posts: Cache<String, Arc<ParsedPage>>,
    /// Blog listings (cache_key -> Vec<BlogPostSummary>)
    pub blog_listings: Cache<String, Arc<Vec<BlogPostSummary>>>,
    /// CMS settings (singleton)
    pub settings: Cache<String, Arc<CmsSettings>>,
    /// Pricing: Vendor agreements (cache_key -> Agreement)
    pub agreements: Cache<String, Arc<Agreement>>,
    /// Pricing: Content types ((app_label, model) -> ContentType)
    pub content_types: Cache<String, Arc<ContentType>>,
}

impl AppCache {
    /// Create a new cache instance with configured TTLs
    pub fn new() -> Self {
        Self {
            // CMS pages: 100 entries, 30 min TTL, 10 min idle
            pages: Cache::builder()
                .max_capacity(100)
                .time_to_live(Duration::from_secs(30 * 60))
                .time_to_idle(Duration::from_secs(10 * 60))
                .build(),

            // Blog posts: 500 entries, 1 hour TTL (rarely changes after publish)
            blog_posts: Cache::builder()
                .max_capacity(500)
                .time_to_live(Duration::from_secs(60 * 60))
                .time_to_idle(Duration::from_secs(30 * 60))
                .build(),

            // Blog listings: 50 entries (categories + pages), 15 min TTL
            blog_listings: Cache::builder()
                .max_capacity(50)
                .time_to_live(Duration::from_secs(15 * 60))
                .time_to_idle(Duration::from_secs(5 * 60))
                .build(),

            // CMS settings: 1 entry, 30 min TTL
            settings: Cache::builder()
                .max_capacity(1)
                .time_to_live(Duration::from_secs(30 * 60))
                .build(),

            // Pricing: Agreements: 200 entries, 1 hour TTL (rarely changes)
            agreements: Cache::builder()
                .max_capacity(200)
                .time_to_live(Duration::from_secs(60 * 60))
                .time_to_idle(Duration::from_secs(30 * 60))
                .build(),

            // Pricing: Content types: 50 entries, 24 hour TTL (almost never changes)
            content_types: Cache::builder()
                .max_capacity(50)
                .time_to_live(Duration::from_secs(24 * 60 * 60))
                .build(),
        }
    }

    /// Generate cache key for agreement lookup
    pub fn agreement_key(scope_type: &str, content_type_id: i32, object_id: &str) -> String {
        format!("{}:{}:{}", scope_type, content_type_id, object_id)
    }

    /// Generate cache key for content type lookup
    pub fn content_type_key(app_label: &str, model: &str) -> String {
        format!("{}:{}", app_label, model)
    }

    /// Get cache statistics for monitoring
    pub fn stats(&self) -> CacheStats {
        CacheStats {
            pages_size: self.pages.entry_count(),
            blog_posts_size: self.blog_posts.entry_count(),
            blog_listings_size: self.blog_listings.entry_count(),
            settings_cached: self.settings.entry_count() > 0,
            agreements_size: self.agreements.entry_count(),
            content_types_size: self.content_types.entry_count(),
        }
    }

    /// Invalidate all caches
    pub fn invalidate_all(&self) {
        self.pages.invalidate_all();
        self.blog_posts.invalidate_all();
        self.blog_listings.invalidate_all();
        self.settings.invalidate_all();
        self.agreements.invalidate_all();
        self.content_types.invalidate_all();
        info!("All caches invalidated");
    }

    /// Invalidate a specific page by slug
    pub async fn invalidate_page(&self, slug: &str) {
        self.pages.invalidate(slug).await;
        self.blog_posts.invalidate(slug).await;
        // Also invalidate blog listings since they might include this post
        self.blog_listings.invalidate_all();
        info!("Cache invalidated for slug: {}", slug);
    }

    /// Generate cache key for blog listing
    pub fn blog_listing_key(category: Option<&str>, page: i64) -> String {
        match category {
            Some(cat) => format!("blog:{}:{}", cat, page),
            None => format!("blog:all:{}", page),
        }
    }
}

impl Default for AppCache {
    fn default() -> Self {
        Self::new()
    }
}

/// Cache statistics for monitoring endpoint
#[derive(Debug, Clone, Serialize)]
pub struct CacheStats {
    pub pages_size: u64,
    pub blog_posts_size: u64,
    pub blog_listings_size: u64,
    pub settings_cached: bool,
    pub agreements_size: u64,
    pub content_types_size: u64,
}

/// Start background cache warmer
///
/// Warms the cache on startup and refreshes every 10 minutes.
pub async fn start_cache_warmer(cache: AppCache, db: PgPool) {
    // Initial warm-up
    warm_cache(&cache, &db).await;

    // Periodic refresh every 10 minutes
    let mut interval = interval(Duration::from_secs(10 * 60));
    loop {
        interval.tick().await;
        warm_cache(&cache, &db).await;
    }
}

/// Warm the cache with commonly accessed data
async fn warm_cache(cache: &AppCache, db: &PgPool) {
    info!("Starting cache warm-up...");

    // Warm CMS settings
    match queries::get_cms_settings(db).await {
        Ok(settings) => {
            cache
                .settings
                .insert("settings".to_string(), Arc::new(settings))
                .await;
        }
        Err(e) => warn!("Failed to warm settings cache: {}", e),
    }

    // Warm homepage
    match queries::get_published_page(db, "home").await {
        Ok(page) => {
            if let Some(parsed) = page.parse() {
                cache
                    .pages
                    .insert("home".to_string(), Arc::new(parsed))
                    .await;
            }
        }
        Err(e) => warn!("Failed to warm homepage cache: {}", e),
    }

    // Warm first page of blog listing
    match queries::get_blog_posts(db, None, 12, 0).await {
        Ok(posts) => {
            let key = AppCache::blog_listing_key(None, 1);
            cache.blog_listings.insert(key, Arc::new(posts)).await;
        }
        Err(e) => warn!("Failed to warm blog listing cache: {}", e),
    }

    // Warm pricing caches
    warm_pricing_cache(cache, db).await;

    info!("Cache warm-up complete. Stats: {:?}", cache.stats());
}

/// Warm pricing-related caches (content types and agreements)
async fn warm_pricing_cache(cache: &AppCache, db: &PgPool) {
    use crate::pricing::queries as pricing_queries;

    // Warm content types (needed for GenericFK resolution)
    match pricing_queries::get_all_content_types(db).await {
        Ok(types) => {
            for ct in types {
                let key = AppCache::content_type_key(&ct.app_label, &ct.model);
                cache.content_types.insert(key, Arc::new(ct)).await;
            }
            info!("Warmed {} content types", cache.content_types.entry_count());
        }
        Err(e) => warn!("Failed to warm content types cache: {}", e),
    }

    // Warm active vendor agreements
    match pricing_queries::get_active_vendor_agreements(db).await {
        Ok(agreements) => {
            for agreement in agreements {
                let key = AppCache::agreement_key(
                    &agreement.scope_type,
                    agreement.scope_ref_content_type_id.unwrap_or(0),
                    &agreement.scope_ref_id,
                );
                cache.agreements.insert(key, Arc::new(agreement)).await;
            }
            info!("Warmed {} agreements", cache.agreements.entry_count());
        }
        Err(e) => warn!("Failed to warm agreements cache: {}", e),
    }
}
