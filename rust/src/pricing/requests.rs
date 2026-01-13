//! Request DTOs for pricing API endpoints.

use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::Deserialize;
use uuid::Uuid;

/// Request to calculate boat cost
#[derive(Debug, Deserialize)]
pub struct CalculateBoatCostRequest {
    pub dive_site_id: Uuid,
    pub diver_count: i32,
    #[serde(default)]
    pub as_of: Option<DateTime<Utc>>,
}

/// Request to calculate gas fills
#[derive(Debug, Deserialize)]
pub struct CalculateGasFillsRequest {
    pub dive_shop_id: Uuid,
    pub gas_type: String,
    pub fills_count: i32,
    #[serde(default, with = "rust_decimal::serde::str_option")]
    pub customer_charge_override: Option<Decimal>,
    #[serde(default)]
    pub as_of: Option<DateTime<Utc>>,
}

/// Request to resolve component pricing
#[derive(Debug, Deserialize)]
pub struct ResolvePricingRequest {
    pub catalog_item_id: Uuid,
    #[serde(default)]
    pub dive_shop_id: Option<Uuid>,
    #[serde(default)]
    pub party_id: Option<Uuid>,
    #[serde(default)]
    pub agreement_id: Option<Uuid>,
    #[serde(default)]
    pub as_of: Option<DateTime<Utc>>,
}

/// Request to allocate shared costs
#[derive(Debug, Deserialize)]
pub struct AllocateSharedCostsRequest {
    #[serde(with = "rust_decimal::serde::str")]
    pub shared_total: Decimal,
    pub diver_count: i32,
    #[serde(default = "default_currency")]
    pub currency: String,
}

fn default_currency() -> String {
    "MXN".to_string()
}

/// Request to calculate full pricing totals
#[derive(Debug, Deserialize)]
pub struct CalculateTotalsRequest {
    pub lines: Vec<PricingLineRequest>,
    pub diver_count: i32,
    #[serde(default = "default_currency")]
    pub currency: String,
    #[serde(default)]
    pub equipment_rentals: Vec<EquipmentRentalRequest>,
}

/// A pricing line in the request
#[derive(Debug, Deserialize)]
pub struct PricingLineRequest {
    pub key: String,
    pub allocation: String,
    #[serde(with = "rust_decimal::serde::str")]
    pub shop_cost_amount: Decimal,
    pub shop_cost_currency: String,
    #[serde(with = "rust_decimal::serde::str")]
    pub customer_charge_amount: Decimal,
    pub customer_charge_currency: String,
}

/// Equipment rental in the request
#[derive(Debug, Deserialize)]
pub struct EquipmentRentalRequest {
    #[serde(with = "rust_decimal::serde::str")]
    pub unit_cost_amount: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    pub unit_charge_amount: Decimal,
    pub quantity: i32,
}
