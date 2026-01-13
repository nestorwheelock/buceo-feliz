//! Pricing service functions with database access.
//!
//! These functions query the database and cache to perform pricing calculations.
//! They mirror the Python implementations in diveops/operations/pricing/calculators.py

use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use sqlx::PgPool;
use std::sync::Arc;
use uuid::Uuid;

use crate::cache::AppCache;

use super::calculators::round_money;
use super::models::Price;
use super::queries;
use super::responses::MoneyResponse;

/// Result of boat cost calculation
#[derive(Debug, Clone)]
pub struct BoatCostResult {
    pub total: MoneyResponse,
    pub per_diver: MoneyResponse,
    pub base_cost: MoneyResponse,
    pub overage_count: i32,
    pub overage_per_diver: MoneyResponse,
    pub included_divers: i32,
    pub diver_count: i32,
    pub agreement_id: Option<String>,
}

/// Result of gas fill pricing
#[derive(Debug, Clone)]
pub struct GasFillResult {
    pub cost_per_fill: MoneyResponse,
    pub charge_per_fill: MoneyResponse,
    pub total_cost: MoneyResponse,
    pub total_charge: MoneyResponse,
    pub fills_count: i32,
    pub gas_type: String,
    pub agreement_id: Option<String>,
    pub price_rule_id: Option<String>,
}

/// Result of component pricing resolution
#[derive(Debug, Clone)]
pub struct ComponentPricingResult {
    pub charge_amount: Decimal,
    pub charge_currency: String,
    pub cost_amount: Option<Decimal>,
    pub cost_currency: String,
    pub price_rule_id: String,
    pub has_cost: bool,
}

/// Pricing calculation error types
#[derive(Debug, Clone)]
pub enum PricingError {
    MissingVendorAgreement {
        scope_type: String,
        scope_ref: String,
    },
    MissingPrice {
        catalog_item_id: String,
        context: String,
    },
    ConfigurationError {
        message: String,
        errors: Vec<String>,
    },
}

impl std::fmt::Display for PricingError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PricingError::MissingVendorAgreement { scope_type, scope_ref } => {
                write!(f, "No vendor agreement found for {}:{}", scope_type, scope_ref)
            }
            PricingError::MissingPrice { catalog_item_id, context } => {
                write!(f, "No price found for catalog item {} ({})", catalog_item_id, context)
            }
            PricingError::ConfigurationError { message, .. } => {
                write!(f, "Configuration error: {}", message)
            }
        }
    }
}

impl std::error::Error for PricingError {}

/// Calculate boat cost using tiered pricing from vendor agreement.
///
/// Looks up the vendor agreement for the given dive site and calculates
/// the total and per-diver boat cost based on the tier structure.
///
/// # Arguments
/// * `pool` - Database connection pool
/// * `cache` - Application cache (for agreement lookup)
/// * `dive_site_id` - UUID of the dive site
/// * `diver_count` - Number of divers on the excursion
/// * `as_of` - Point in time for pricing (default: now)
///
/// # Returns
/// `BoatCostResult` with breakdown
pub async fn calculate_boat_cost(
    pool: &PgPool,
    cache: &AppCache,
    dive_site_content_type_id: i32,
    dive_site_id: Uuid,
    diver_count: i32,
    as_of: Option<DateTime<Utc>>,
) -> Result<BoatCostResult, PricingError> {
    if diver_count <= 0 {
        return Err(PricingError::ConfigurationError {
            message: "Diver count must be positive".to_string(),
            errors: vec!["diver_count <= 0".to_string()],
        });
    }

    let check_time = as_of.unwrap_or_else(Utc::now);

    // Try cache first
    let cache_key = AppCache::agreement_key(
        "vendor_pricing",
        dive_site_content_type_id,
        &dive_site_id.to_string(),
    );

    let agreement = if let Some(cached) = cache.agreements.get(&cache_key).await {
        if cached.is_valid_at(check_time) {
            Some((*cached).clone())
        } else {
            None
        }
    } else {
        None
    };

    // If not in cache (or invalid), query database
    let agreement = match agreement {
        Some(a) => a,
        None => {
            let result = queries::find_vendor_agreement(
                pool,
                "vendor_pricing",
                dive_site_content_type_id,
                &dive_site_id.to_string(),
                check_time,
            )
            .await
            .map_err(|_| PricingError::MissingVendorAgreement {
                scope_type: "vendor_pricing".to_string(),
                scope_ref: format!("DiveSite:{}", dive_site_id),
            })?
            .ok_or_else(|| PricingError::MissingVendorAgreement {
                scope_type: "vendor_pricing".to_string(),
                scope_ref: format!("DiveSite:{}", dive_site_id),
            })?;

            // Cache the result
            cache
                .agreements
                .insert(cache_key, Arc::new(result.clone()))
                .await;

            result
        }
    };

    // Extract boat tier from agreement terms
    let boat_tier = agreement
        .terms
        .get("boat_charter")
        .ok_or_else(|| PricingError::ConfigurationError {
            message: format!("Agreement {} missing 'boat_charter' in terms", agreement.id),
            errors: vec!["boat_charter not in agreement.terms".to_string()],
        })?;

    // Parse tier structure
    let base_cost = boat_tier
        .get("base_cost")
        .and_then(|v| v.as_str().or_else(|| v.as_f64().map(|_| "")))
        .map(|s| if s.is_empty() {
            boat_tier.get("base_cost").and_then(|v| v.as_f64()).map(|f| Decimal::try_from(f).unwrap_or(Decimal::ZERO)).unwrap_or(Decimal::ZERO)
        } else {
            s.parse::<Decimal>().unwrap_or(Decimal::ZERO)
        })
        .unwrap_or(Decimal::ZERO);

    let included_divers = boat_tier
        .get("included_divers")
        .and_then(|v| v.as_i64())
        .map(|v| v as i32)
        .unwrap_or(4);

    let overage_per_diver = boat_tier
        .get("overage_per_diver")
        .and_then(|v| v.as_str().or_else(|| v.as_f64().map(|_| "")))
        .map(|s| if s.is_empty() {
            boat_tier.get("overage_per_diver").and_then(|v| v.as_f64()).map(|f| Decimal::try_from(f).unwrap_or(Decimal::ZERO)).unwrap_or(Decimal::ZERO)
        } else {
            s.parse::<Decimal>().unwrap_or(Decimal::ZERO)
        })
        .unwrap_or(Decimal::ZERO);

    let currency = boat_tier
        .get("currency")
        .and_then(|v| v.as_str())
        .unwrap_or("MXN")
        .to_string();

    // Calculate total boat cost
    let (total_amount, overage_count) = if diver_count <= included_divers {
        (base_cost, 0)
    } else {
        let overage = diver_count - included_divers;
        (base_cost + (Decimal::from(overage) * overage_per_diver), overage)
    };

    // Calculate per-diver share (banker's rounding)
    let per_diver_amount = round_money(total_amount / Decimal::from(diver_count), 2);

    Ok(BoatCostResult {
        total: MoneyResponse {
            amount: total_amount,
            currency: currency.clone(),
        },
        per_diver: MoneyResponse {
            amount: per_diver_amount,
            currency: currency.clone(),
        },
        base_cost: MoneyResponse {
            amount: base_cost,
            currency: currency.clone(),
        },
        overage_count,
        overage_per_diver: MoneyResponse {
            amount: overage_per_diver,
            currency: currency.clone(),
        },
        included_divers,
        diver_count,
        agreement_id: Some(agreement.id.to_string()),
    })
}

/// Calculate gas fill costs from vendor agreement.
///
/// # Arguments
/// * `pool` - Database connection pool
/// * `cache` - Application cache
/// * `dive_shop_content_type_id` - ContentType ID for Organization
/// * `dive_shop_id` - UUID of the dive shop (Organization)
/// * `gas_type` - Type of gas (air, ean32, ean36, trimix)
/// * `fills_count` - Number of tank fills
/// * `customer_charge_override` - Optional override for customer charge
/// * `as_of` - Point in time for pricing
pub async fn calculate_gas_fills(
    pool: &PgPool,
    _cache: &AppCache,
    dive_shop_content_type_id: i32,
    dive_shop_id: Uuid,
    gas_type: &str,
    fills_count: i32,
    customer_charge_override: Option<Decimal>,
    as_of: Option<DateTime<Utc>>,
) -> Result<GasFillResult, PricingError> {
    if fills_count <= 0 {
        return Err(PricingError::ConfigurationError {
            message: "Fills count must be positive".to_string(),
            errors: vec!["fills_count <= 0".to_string()],
        });
    }

    let check_time = as_of.unwrap_or_else(Utc::now);
    let gas_type_lower = gas_type.to_lowercase();

    // Find active gas vendor agreement for dive shop
    let agreement = queries::find_gas_vendor_agreement(
        pool,
        dive_shop_content_type_id,
        &dive_shop_id.to_string(),
        check_time,
    )
    .await
    .map_err(|_| PricingError::MissingVendorAgreement {
        scope_type: "gas_vendor_pricing".to_string(),
        scope_ref: format!("Organization:{}", dive_shop_id),
    })?
    .ok_or_else(|| PricingError::MissingVendorAgreement {
        scope_type: "gas_vendor_pricing".to_string(),
        scope_ref: format!("Organization:{}", dive_shop_id),
    })?;

    // Extract gas pricing from agreement terms
    let gas_fills = agreement
        .terms
        .get("gas_fills")
        .ok_or_else(|| PricingError::ConfigurationError {
            message: format!("Agreement {} missing 'gas_fills' in terms", agreement.id),
            errors: vec!["gas_fills not in agreement.terms".to_string()],
        })?;

    let gas_pricing = gas_fills
        .get(&gas_type_lower)
        .ok_or_else(|| PricingError::ConfigurationError {
            message: format!(
                "Agreement {} missing pricing for gas type '{}'",
                agreement.id, gas_type
            ),
            errors: vec![format!("gas_fills.{} not in agreement.terms", gas_type_lower)],
        })?;

    // Parse pricing
    let cost_per_fill = gas_pricing
        .get("cost")
        .and_then(|v| v.as_str().or_else(|| v.as_f64().map(|_| "")))
        .map(|s| if s.is_empty() {
            gas_pricing.get("cost").and_then(|v| v.as_f64()).map(|f| Decimal::try_from(f).unwrap_or(Decimal::ZERO)).unwrap_or(Decimal::ZERO)
        } else {
            s.parse::<Decimal>().unwrap_or(Decimal::ZERO)
        })
        .unwrap_or(Decimal::ZERO);

    let currency = gas_pricing
        .get("currency")
        .and_then(|v| v.as_str())
        .unwrap_or("MXN")
        .to_string();

    // Customer charge - use override if provided, else from agreement
    let charge_per_fill = if let Some(override_charge) = customer_charge_override {
        override_charge
    } else {
        gas_pricing
            .get("charge")
            .and_then(|v| v.as_str().or_else(|| v.as_f64().map(|_| "")))
            .map(|s| if s.is_empty() {
                gas_pricing.get("charge").and_then(|v| v.as_f64()).map(|f| Decimal::try_from(f).unwrap_or(Decimal::ZERO)).unwrap_or(Decimal::ZERO)
            } else {
                s.parse::<Decimal>().unwrap_or(Decimal::ZERO)
            })
            .unwrap_or(Decimal::ZERO)
    };

    // Calculate totals
    let total_cost = cost_per_fill * Decimal::from(fills_count);
    let total_charge = charge_per_fill * Decimal::from(fills_count);

    Ok(GasFillResult {
        cost_per_fill: MoneyResponse {
            amount: cost_per_fill,
            currency: currency.clone(),
        },
        charge_per_fill: MoneyResponse {
            amount: charge_per_fill,
            currency: currency.clone(),
        },
        total_cost: MoneyResponse {
            amount: total_cost,
            currency: currency.clone(),
        },
        total_charge: MoneyResponse {
            amount: total_charge,
            currency: currency.clone(),
        },
        fills_count,
        gas_type: gas_type.to_string(),
        agreement_id: Some(agreement.id.to_string()),
        price_rule_id: None,
    })
}

/// Resolve pricing for a catalog item component.
///
/// Uses the Price model's resolution hierarchy:
/// 1. Agreement-specific
/// 2. Party-specific
/// 3. Organization-specific
/// 4. Global
///
/// # Arguments
/// * `pool` - Database connection pool
/// * `catalog_item_id` - UUID of the catalog item to price
/// * `organization_id` - Optional organization for org-scoped pricing
/// * `party_id` - Optional party for party-scoped pricing
/// * `agreement_id` - Optional agreement for agreement-scoped pricing
/// * `as_of` - Point in time for pricing
pub async fn resolve_component_pricing(
    pool: &PgPool,
    catalog_item_id: Uuid,
    organization_id: Option<Uuid>,
    party_id: Option<Uuid>,
    agreement_id: Option<Uuid>,
    as_of: Option<DateTime<Utc>>,
) -> Result<ComponentPricingResult, PricingError> {
    let check_time = as_of.unwrap_or_else(Utc::now);

    let price: Option<Price> = None;

    // Try resolution in priority order
    // 1. Agreement-specific
    let price = if let (None, Some(agreement)) = (&price, agreement_id) {
        queries::find_price_by_agreement(pool, catalog_item_id, agreement, check_time)
            .await
            .ok()
            .flatten()
    } else {
        price
    };

    // 2. Party-specific
    let price = if let (None, Some(party)) = (&price, party_id) {
        queries::find_price_by_party(pool, catalog_item_id, party, check_time)
            .await
            .ok()
            .flatten()
    } else {
        price
    };

    // 3. Organization-specific
    let price = if let (None, Some(org)) = (&price, organization_id) {
        queries::find_price_by_organization(pool, catalog_item_id, org, check_time)
            .await
            .ok()
            .flatten()
    } else {
        price
    };

    // 4. Global fallback
    let price = if price.is_none() {
        queries::find_global_price(pool, catalog_item_id, check_time)
            .await
            .ok()
            .flatten()
    } else {
        price
    };

    let price = price.ok_or_else(|| PricingError::MissingPrice {
        catalog_item_id: catalog_item_id.to_string(),
        context: "No price found at any scope level".to_string(),
    })?;

    Ok(ComponentPricingResult {
        charge_amount: price.amount,
        charge_currency: price.currency.clone(),
        cost_amount: price.cost_amount,
        cost_currency: price.cost_currency.unwrap_or_else(|| price.currency.clone()),
        price_rule_id: price.id.to_string(),
        has_cost: price.cost_amount.is_some(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pricing_error_display() {
        let err = PricingError::MissingVendorAgreement {
            scope_type: "vendor_pricing".to_string(),
            scope_ref: "DiveSite:abc".to_string(),
        };
        assert!(err.to_string().contains("vendor_pricing"));

        let err = PricingError::MissingPrice {
            catalog_item_id: "123".to_string(),
            context: "test".to_string(),
        };
        assert!(err.to_string().contains("123"));

        let err = PricingError::ConfigurationError {
            message: "test error".to_string(),
            errors: vec![],
        };
        assert!(err.to_string().contains("test error"));
    }

    #[test]
    fn test_boat_cost_validation() {
        // Validation tests that don't need database
        // The actual DB tests would be integration tests
    }
}
