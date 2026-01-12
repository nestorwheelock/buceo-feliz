//! Blog route handlers

use askama::Template;
use axum::{
    extract::{Path, Query, State},
    response::Html,
};
use serde::Deserialize;

use crate::db;
use crate::error::Result;
use crate::models::{Block, BlogCategory, BlogPostSummary};
use crate::AppState;

/// Query parameters for blog listing
#[derive(Debug, Deserialize)]
pub struct BlogListQuery {
    #[serde(default = "default_page")]
    pub page: i64,
}

fn default_page() -> i64 {
    1
}

const POSTS_PER_PAGE: i64 = 9;

/// Blog listing template
#[derive(Template)]
#[template(path = "blog/list.html")]
struct BlogListTemplate {
    posts: Vec<BlogPostSummary>,
    categories: Vec<BlogCategory>,
    current_category: Option<String>,
    page: i64,
    total_pages: i64,
    has_previous: bool,
    has_next: bool,
    has_categories: bool,
    has_posts: bool,
    no_category_selected: bool,
}

/// Blog detail template
#[derive(Template)]
#[template(path = "blog/detail.html")]
struct BlogDetailTemplate {
    post: BlogPostSummary,
    blocks: Vec<Block>,
    categories: Vec<BlogCategory>,
    related_posts: Vec<BlogPostSummary>,
    seo_title: String,
    seo_description: String,
    og_image_url: String,
    has_og_image: bool,
}

/// Blog listing page
pub async fn list(
    State(state): State<AppState>,
    Query(query): Query<BlogListQuery>,
) -> Result<Html<String>> {
    let offset = (query.page - 1) * POSTS_PER_PAGE;

    let posts = db::get_blog_posts(&state.db, None, POSTS_PER_PAGE, offset).await?;
    let categories = db::get_blog_categories(&state.db).await?;
    let total = db::count_blog_posts(&state.db, None).await?;
    let total_pages = (total + POSTS_PER_PAGE - 1) / POSTS_PER_PAGE;

    let template = BlogListTemplate {
        has_categories: !categories.is_empty(),
        has_posts: !posts.is_empty(),
        no_category_selected: true,
        posts,
        categories,
        current_category: None,
        page: query.page,
        total_pages,
        has_previous: query.page > 1,
        has_next: query.page < total_pages,
    };

    Ok(Html(template.render().unwrap()))
}

/// Blog listing by category
pub async fn by_category(
    State(state): State<AppState>,
    Path(category): Path<String>,
    Query(query): Query<BlogListQuery>,
) -> Result<Html<String>> {
    let offset = (query.page - 1) * POSTS_PER_PAGE;

    let posts = db::get_blog_posts(&state.db, Some(&category), POSTS_PER_PAGE, offset).await?;
    let categories = db::get_blog_categories(&state.db).await?;
    let total = db::count_blog_posts(&state.db, Some(&category)).await?;
    let total_pages = (total + POSTS_PER_PAGE - 1) / POSTS_PER_PAGE;

    let template = BlogListTemplate {
        has_categories: !categories.is_empty(),
        has_posts: !posts.is_empty(),
        no_category_selected: false,
        posts,
        categories,
        current_category: Some(category),
        page: query.page,
        total_pages,
        has_previous: query.page > 1,
        has_next: query.page < total_pages,
    };

    Ok(Html(template.render().unwrap()))
}

/// Blog detail page
pub async fn detail(
    State(state): State<AppState>,
    Path(slug): Path<String>,
) -> Result<Html<String>> {
    let page = db::get_blog_post(&state.db, &slug).await?;
    let categories = db::get_blog_categories(&state.db).await?;

    // Parse the published snapshot
    let parsed = page.parse().ok_or(crate::error::AppError::NotFound)?;

    // Get related posts (same category)
    let related_posts = db::get_blog_posts(&state.db, None, 3, 0).await?;

    let has_og_image = !parsed.meta.og_image_url.is_empty();

    let template = BlogDetailTemplate {
        post: BlogPostSummary {
            slug: parsed.slug,
            title: parsed.title,
            excerpt: parsed.meta.seo_description.clone(),
            featured_image_url: if parsed.meta.og_image_url.is_empty() {
                None
            } else {
                Some(parsed.meta.og_image_url.clone())
            },
            category_name: None,
            category_slug: None,
            category_color: None,
            published_at: None,
            reading_time_minutes: None,
        },
        blocks: parsed.blocks,
        categories,
        related_posts,
        seo_title: if parsed.meta.seo_title.is_empty() {
            format!("{} | Happy Diving", parsed.meta.title)
        } else {
            parsed.meta.seo_title
        },
        seo_description: parsed.meta.seo_description,
        og_image_url: parsed.meta.og_image_url,
        has_og_image,
    };

    Ok(Html(template.render().unwrap()))
}
