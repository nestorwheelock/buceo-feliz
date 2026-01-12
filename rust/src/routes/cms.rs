//! CMS page route handlers

use askama::Template;
use axum::{
    extract::{Path, State},
    response::Html,
};
use std::sync::Arc;

use crate::db;
use crate::error::Result;
use crate::models::{Block, ParsedPage};
use crate::AppState;

/// CMS page template
#[derive(Template)]
#[template(path = "cms/page.html")]
struct CmsPageTemplate {
    title: String,
    blocks: Vec<Block>,
    seo_title: String,
    seo_description: String,
    og_image_url: String,
    robots: String,
    has_og_image: bool,
}

/// Homepage handler
pub async fn home(State(state): State<AppState>) -> Result<Html<String>> {
    render_page(&state, "home").await
}

/// CMS page handler (catch-all for slugs)
pub async fn page(
    State(state): State<AppState>,
    Path(slug): Path<String>,
) -> Result<Html<String>> {
    render_page(&state, &slug).await
}

/// Internal function to render a CMS page
async fn render_page(state: &AppState, slug: &str) -> Result<Html<String>> {
    // Try cache first
    let parsed: ParsedPage = if let Some(cached) = state.cache.pages.get(slug).await {
        tracing::debug!("Cache HIT for CMS page: {}", slug);
        (*cached).clone()
    } else {
        tracing::debug!("Cache MISS for CMS page: {}", slug);
        let page = db::get_published_page(&state.db, slug).await?;
        let parsed = page.parse().ok_or(crate::error::AppError::NotFound)?;
        state.cache.pages.insert(slug.to_string(), Arc::new(parsed.clone())).await;
        parsed
    };

    let has_og_image = !parsed.meta.og_image_url.is_empty();

    let template = CmsPageTemplate {
        title: parsed.title,
        blocks: parsed.blocks,
        seo_title: if parsed.meta.seo_title.is_empty() {
            format!("{} | Happy Diving", parsed.meta.title)
        } else {
            parsed.meta.seo_title
        },
        seo_description: parsed.meta.seo_description,
        og_image_url: parsed.meta.og_image_url,
        robots: parsed.meta.robots,
        has_og_image,
    };

    Ok(Html(template.render().unwrap()))
}
