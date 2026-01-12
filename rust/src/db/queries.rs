//! Database queries for CMS and blog content

use sqlx::PgPool;

use crate::error::{AppError, Result};
use crate::models::{BlogCategory, BlogPostSummary, CmsPage, CmsSettings};

/// Get a published CMS page by slug
pub async fn get_published_page(pool: &PgPool, slug: &str) -> Result<CmsPage> {
    let page = sqlx::query_as::<_, CmsPage>(
        r#"
        SELECT
            id,
            slug,
            title,
            page_type,
            status,
            seo_title,
            seo_description,
            og_image_url,
            robots,
            published_snapshot,
            published_at,
            template_key
        FROM django_cms_core_contentpage
        WHERE slug = $1
          AND status = 'published'
          AND page_type = 'page'
          AND deleted_at IS NULL
        "#,
    )
    .bind(slug)
    .fetch_optional(pool)
    .await?
    .ok_or(AppError::NotFound)?;

    Ok(page)
}

/// Get a published blog post by slug
pub async fn get_blog_post(pool: &PgPool, slug: &str) -> Result<CmsPage> {
    let page = sqlx::query_as::<_, CmsPage>(
        r#"
        SELECT
            id,
            slug,
            title,
            page_type,
            status,
            seo_title,
            seo_description,
            og_image_url,
            robots,
            published_snapshot,
            published_at,
            template_key
        FROM django_cms_core_contentpage
        WHERE slug = $1
          AND status = 'published'
          AND page_type = 'post'
          AND deleted_at IS NULL
        "#,
    )
    .bind(slug)
    .fetch_optional(pool)
    .await?
    .ok_or(AppError::NotFound)?;

    Ok(page)
}

/// Get blog posts with optional category filter
pub async fn get_blog_posts(
    pool: &PgPool,
    category_slug: Option<&str>,
    limit: i64,
    offset: i64,
) -> Result<Vec<BlogPostSummary>> {
    let posts = match category_slug {
        Some(cat) => {
            sqlx::query_as::<_, BlogPostSummary>(
                r#"
                SELECT
                    p.slug,
                    p.title,
                    p.excerpt,
                    p.featured_image_url,
                    c.name as category_name,
                    c.slug as category_slug,
                    c.color as category_color,
                    p.published_at,
                    p.reading_time_minutes
                FROM django_cms_core_contentpage p
                LEFT JOIN django_cms_core_blogcategory c ON p.category_id = c.id AND c.deleted_at IS NULL
                WHERE p.page_type = 'post'
                  AND p.status = 'published'
                  AND p.deleted_at IS NULL
                  AND c.slug = $1
                ORDER BY p.published_at DESC NULLS LAST
                LIMIT $2 OFFSET $3
                "#,
            )
            .bind(cat)
            .bind(limit)
            .bind(offset)
            .fetch_all(pool)
            .await?
        }
        None => {
            sqlx::query_as::<_, BlogPostSummary>(
                r#"
                SELECT
                    p.slug,
                    p.title,
                    p.excerpt,
                    p.featured_image_url,
                    c.name as category_name,
                    c.slug as category_slug,
                    c.color as category_color,
                    p.published_at,
                    p.reading_time_minutes
                FROM django_cms_core_contentpage p
                LEFT JOIN django_cms_core_blogcategory c ON p.category_id = c.id AND c.deleted_at IS NULL
                WHERE p.page_type = 'post'
                  AND p.status = 'published'
                  AND p.deleted_at IS NULL
                ORDER BY p.published_at DESC NULLS LAST
                LIMIT $1 OFFSET $2
                "#,
            )
            .bind(limit)
            .bind(offset)
            .fetch_all(pool)
            .await?
        }
    };

    Ok(posts)
}

/// Get all blog categories
pub async fn get_blog_categories(pool: &PgPool) -> Result<Vec<BlogCategory>> {
    let categories = sqlx::query_as::<_, BlogCategory>(
        r#"
        SELECT id, name, slug, description, color, sort_order
        FROM django_cms_core_blogcategory
        WHERE deleted_at IS NULL
        ORDER BY sort_order, name
        "#,
    )
    .fetch_all(pool)
    .await?;

    Ok(categories)
}

/// Get CMS settings
pub async fn get_cms_settings(pool: &PgPool) -> Result<CmsSettings> {
    let settings = sqlx::query_as::<_, CmsSettings>(
        r#"
        SELECT
            site_name,
            default_seo_title_suffix,
            default_og_image_url,
            nav_json,
            footer_json
        FROM django_cms_core_cmssettings
        LIMIT 1
        "#,
    )
    .fetch_optional(pool)
    .await?
    .unwrap_or_default();

    Ok(settings)
}

/// Count blog posts (for pagination)
pub async fn count_blog_posts(pool: &PgPool, category_slug: Option<&str>) -> Result<i64> {
    let count: i64 = match category_slug {
        Some(cat) => {
            sqlx::query_scalar(
                r#"
                SELECT COUNT(*)
                FROM django_cms_core_contentpage p
                JOIN django_cms_core_blogcategory c ON p.category_id = c.id AND c.deleted_at IS NULL
                WHERE p.page_type = 'post'
                  AND p.status = 'published'
                  AND p.deleted_at IS NULL
                  AND c.slug = $1
                "#,
            )
            .bind(cat)
            .fetch_one(pool)
            .await?
        }
        None => {
            sqlx::query_scalar(
                r#"
                SELECT COUNT(*)
                FROM django_cms_core_contentpage
                WHERE page_type = 'post'
                  AND status = 'published'
                  AND deleted_at IS NULL
                "#,
            )
            .fetch_one(pool)
            .await?
        }
    };

    Ok(count)
}
