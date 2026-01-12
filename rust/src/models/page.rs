//! CMS page models

use chrono::{DateTime, Utc};
use serde::Serialize;
use sqlx::FromRow;
use uuid::Uuid;

use super::blog::{Block, PageMeta, PublishedSnapshot};

/// CMS page from database
#[derive(Debug, Clone, FromRow)]
pub struct CmsPage {
    pub id: Uuid,
    pub slug: String,
    pub title: String,
    pub page_type: String,
    pub status: String,
    pub seo_title: String,
    pub seo_description: String,
    pub og_image_url: String,
    pub robots: String,
    pub published_snapshot: Option<serde_json::Value>,
    pub published_at: Option<DateTime<Utc>>,
    pub template_key: String,
}

/// CMS settings singleton
#[derive(Debug, Clone, FromRow, Serialize)]
pub struct CmsSettings {
    pub site_name: String,
    pub default_seo_title_suffix: String,
    pub default_og_image_url: String,
    pub nav_json: serde_json::Value,
    pub footer_json: serde_json::Value,
}

impl Default for CmsSettings {
    fn default() -> Self {
        Self {
            site_name: "Happy Diving".to_string(),
            default_seo_title_suffix: " | Happy Diving".to_string(),
            default_og_image_url: String::new(),
            nav_json: serde_json::json!([]),
            footer_json: serde_json::json!({}),
        }
    }
}

/// Parsed CMS page ready for rendering
#[derive(Debug, Clone, Serialize)]
pub struct ParsedPage {
    pub slug: String,
    pub title: String,
    pub meta: PageMeta,
    pub blocks: Vec<Block>,
    pub template_key: String,
}

impl CmsPage {
    /// Parse the published snapshot into a renderable page
    pub fn parse(self) -> Option<ParsedPage> {
        let snapshot: PublishedSnapshot = self.published_snapshot
            .and_then(|v| serde_json::from_value(v).ok())?;

        Some(ParsedPage {
            slug: self.slug,
            title: self.title,
            meta: snapshot.meta,
            blocks: snapshot.blocks,
            template_key: self.template_key,
        })
    }
}
