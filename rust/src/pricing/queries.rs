//! Database queries for pricing engine.
//!
//! All queries use sqlx with compile-time validation.

use chrono::{DateTime, Utc};
use sqlx::PgPool;
use uuid::Uuid;

use crate::error::AppError;

use super::models::{Agreement, CatalogItem, ContentType, Price};

/// Get a content type by app_label and model name
pub async fn get_content_type(
    pool: &PgPool,
    app_label: &str,
    model: &str,
) -> Result<ContentType, AppError> {
    sqlx::query_as::<_, ContentType>(
        r#"
        SELECT id, app_label, model
        FROM django_content_type
        WHERE app_label = $1 AND model = $2
        "#,
    )
    .bind(app_label)
    .bind(model)
    .fetch_optional(pool)
    .await?
    .ok_or_else(|| AppError::NotFound)
}

/// Find a vendor agreement by scope
pub async fn find_vendor_agreement(
    pool: &PgPool,
    scope_type: &str,
    scope_ref_content_type_id: i32,
    scope_ref_id: &str,
    check_time: DateTime<Utc>,
) -> Result<Option<Agreement>, AppError> {
    let agreement = sqlx::query_as::<_, Agreement>(
        r#"
        SELECT
            id, party_a_content_type_id, party_a_id,
            party_b_content_type_id, party_b_id,
            scope_type, scope_ref_content_type_id, scope_ref_id,
            terms, valid_from, valid_to, current_version, deleted_at
        FROM django_agreements_agreement
        WHERE scope_type = $1
          AND scope_ref_content_type_id = $2
          AND scope_ref_id = $3
          AND valid_from <= $4
          AND (valid_to IS NULL OR valid_to > $4)
          AND deleted_at IS NULL
        ORDER BY valid_from DESC
        LIMIT 1
        "#,
    )
    .bind(scope_type)
    .bind(scope_ref_content_type_id)
    .bind(scope_ref_id)
    .bind(check_time)
    .fetch_optional(pool)
    .await?;

    Ok(agreement)
}

/// Find a gas vendor agreement by party_a (dive shop)
pub async fn find_gas_vendor_agreement(
    pool: &PgPool,
    party_a_content_type_id: i32,
    party_a_id: &str,
    check_time: DateTime<Utc>,
) -> Result<Option<Agreement>, AppError> {
    let agreement = sqlx::query_as::<_, Agreement>(
        r#"
        SELECT
            id, party_a_content_type_id, party_a_id,
            party_b_content_type_id, party_b_id,
            scope_type, scope_ref_content_type_id, scope_ref_id,
            terms, valid_from, valid_to, current_version, deleted_at
        FROM django_agreements_agreement
        WHERE scope_type = 'gas_vendor_pricing'
          AND party_a_content_type_id = $1
          AND party_a_id = $2
          AND valid_from <= $3
          AND (valid_to IS NULL OR valid_to > $3)
          AND deleted_at IS NULL
        ORDER BY valid_from DESC
        LIMIT 1
        "#,
    )
    .bind(party_a_content_type_id)
    .bind(party_a_id)
    .bind(check_time)
    .fetch_optional(pool)
    .await?;

    Ok(agreement)
}

/// Find price by agreement scope (highest priority)
pub async fn find_price_by_agreement(
    pool: &PgPool,
    catalog_item_id: Uuid,
    agreement_id: Uuid,
    check_time: DateTime<Utc>,
) -> Result<Option<Price>, AppError> {
    let price = sqlx::query_as::<_, Price>(
        r#"
        SELECT
            id, catalog_item_id, amount, currency,
            cost_amount, cost_currency,
            organization_id, party_id, agreement_id,
            valid_from, valid_to, priority
        FROM pricing_price
        WHERE catalog_item_id = $1
          AND agreement_id = $2
          AND valid_from <= $3
          AND (valid_to IS NULL OR valid_to > $3)
        ORDER BY priority DESC, valid_from DESC
        LIMIT 1
        "#,
    )
    .bind(catalog_item_id)
    .bind(agreement_id)
    .bind(check_time)
    .fetch_optional(pool)
    .await?;

    Ok(price)
}

/// Find price by party scope
pub async fn find_price_by_party(
    pool: &PgPool,
    catalog_item_id: Uuid,
    party_id: Uuid,
    check_time: DateTime<Utc>,
) -> Result<Option<Price>, AppError> {
    let price = sqlx::query_as::<_, Price>(
        r#"
        SELECT
            id, catalog_item_id, amount, currency,
            cost_amount, cost_currency,
            organization_id, party_id, agreement_id,
            valid_from, valid_to, priority
        FROM pricing_price
        WHERE catalog_item_id = $1
          AND party_id = $2
          AND agreement_id IS NULL
          AND valid_from <= $3
          AND (valid_to IS NULL OR valid_to > $3)
        ORDER BY priority DESC, valid_from DESC
        LIMIT 1
        "#,
    )
    .bind(catalog_item_id)
    .bind(party_id)
    .bind(check_time)
    .fetch_optional(pool)
    .await?;

    Ok(price)
}

/// Find price by organization scope
pub async fn find_price_by_organization(
    pool: &PgPool,
    catalog_item_id: Uuid,
    organization_id: Uuid,
    check_time: DateTime<Utc>,
) -> Result<Option<Price>, AppError> {
    let price = sqlx::query_as::<_, Price>(
        r#"
        SELECT
            id, catalog_item_id, amount, currency,
            cost_amount, cost_currency,
            organization_id, party_id, agreement_id,
            valid_from, valid_to, priority
        FROM pricing_price
        WHERE catalog_item_id = $1
          AND organization_id = $2
          AND party_id IS NULL
          AND agreement_id IS NULL
          AND valid_from <= $3
          AND (valid_to IS NULL OR valid_to > $3)
        ORDER BY priority DESC, valid_from DESC
        LIMIT 1
        "#,
    )
    .bind(catalog_item_id)
    .bind(organization_id)
    .bind(check_time)
    .fetch_optional(pool)
    .await?;

    Ok(price)
}

/// Find global price (no scope)
pub async fn find_global_price(
    pool: &PgPool,
    catalog_item_id: Uuid,
    check_time: DateTime<Utc>,
) -> Result<Option<Price>, AppError> {
    let price = sqlx::query_as::<_, Price>(
        r#"
        SELECT
            id, catalog_item_id, amount, currency,
            cost_amount, cost_currency,
            organization_id, party_id, agreement_id,
            valid_from, valid_to, priority
        FROM pricing_price
        WHERE catalog_item_id = $1
          AND organization_id IS NULL
          AND party_id IS NULL
          AND agreement_id IS NULL
          AND valid_from <= $3
          AND (valid_to IS NULL OR valid_to > $3)
        ORDER BY priority DESC, valid_from DESC
        LIMIT 1
        "#,
    )
    .bind(catalog_item_id)
    .bind(check_time)
    .fetch_optional(pool)
    .await?;

    Ok(price)
}

/// Get catalog item by display name
pub async fn get_catalog_item_by_name(
    pool: &PgPool,
    display_name: &str,
) -> Result<Option<CatalogItem>, AppError> {
    let item = sqlx::query_as::<_, CatalogItem>(
        r#"
        SELECT id, display_name, active, deleted_at
        FROM django_catalog_catalogitem
        WHERE display_name = $1
          AND active = true
          AND deleted_at IS NULL
        "#,
    )
    .bind(display_name)
    .fetch_optional(pool)
    .await?;

    Ok(item)
}

/// Get all content types (for cache warming)
pub async fn get_all_content_types(pool: &PgPool) -> Result<Vec<ContentType>, AppError> {
    let types = sqlx::query_as::<_, ContentType>(
        r#"
        SELECT id, app_label, model
        FROM django_content_type
        "#,
    )
    .fetch_all(pool)
    .await?;

    Ok(types)
}

/// Get all active vendor agreements (for cache warming)
pub async fn get_active_vendor_agreements(pool: &PgPool) -> Result<Vec<Agreement>, AppError> {
    let now = Utc::now();
    let agreements = sqlx::query_as::<_, Agreement>(
        r#"
        SELECT
            id, party_a_content_type_id, party_a_id,
            party_b_content_type_id, party_b_id,
            scope_type, scope_ref_content_type_id, scope_ref_id,
            terms, valid_from, valid_to, current_version, deleted_at
        FROM django_agreements_agreement
        WHERE scope_type IN ('vendor_pricing', 'gas_vendor_pricing')
          AND valid_from <= $1
          AND (valid_to IS NULL OR valid_to > $1)
          AND deleted_at IS NULL
        "#,
    )
    .bind(now)
    .fetch_all(pool)
    .await?;

    Ok(agreements)
}

/// Get content type ID for a model (used for GenericFK lookups)
pub async fn get_content_type_id(
    pool: &PgPool,
    app_label: &str,
    model: &str,
) -> Result<i32, AppError> {
    let content_type = get_content_type(pool, app_label, model).await?;
    Ok(content_type.id)
}
