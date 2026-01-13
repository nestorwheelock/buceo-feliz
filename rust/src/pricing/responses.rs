//! Response DTOs for pricing API endpoints.

use rust_decimal::Decimal;
use serde::Serialize;
use uuid::Uuid;

/// Money value for JSON responses
#[derive(Debug, Clone, Serialize)]
pub struct MoneyResponse {
    #[serde(with = "rust_decimal::serde::str")]
    pub amount: Decimal,
    pub currency: String,
}

/// Response for boat cost calculation
#[derive(Debug, Serialize)]
pub struct BoatCostResponse {
    pub total: MoneyResponse,
    pub per_diver: MoneyResponse,
    pub base_cost: MoneyResponse,
    pub overage_count: i32,
    pub overage_per_diver: MoneyResponse,
    pub included_divers: i32,
    pub diver_count: i32,
    pub agreement_id: Option<Uuid>,
}

/// Response for gas fill calculation
#[derive(Debug, Serialize)]
pub struct GasFillResponse {
    pub cost_per_fill: MoneyResponse,
    pub charge_per_fill: MoneyResponse,
    pub total_cost: MoneyResponse,
    pub total_charge: MoneyResponse,
    pub fills_count: i32,
    pub gas_type: String,
    pub agreement_id: Option<Uuid>,
    pub price_rule_id: Option<Uuid>,
}

/// Response for component pricing resolution
#[derive(Debug, Serialize)]
pub struct PricingResolutionResponse {
    #[serde(with = "rust_decimal::serde::str")]
    pub charge_amount: Decimal,
    pub charge_currency: String,
    #[serde(with = "rust_decimal::serde::str_option")]
    pub cost_amount: Option<Decimal>,
    pub cost_currency: String,
    pub price_rule_id: Uuid,
    pub has_cost: bool,
}

/// Response for shared cost allocation
#[derive(Debug, Serialize)]
pub struct AllocationResponse {
    pub per_diver: MoneyResponse,
    pub amounts: Vec<MoneyResponse>,
}

/// Response for pricing totals
#[derive(Debug, Serialize)]
pub struct PricingTotalsResponse {
    pub shared_cost: MoneyResponse,
    pub shared_charge: MoneyResponse,
    pub per_diver_cost: MoneyResponse,
    pub per_diver_charge: MoneyResponse,
    pub shared_cost_per_diver: MoneyResponse,
    pub shared_charge_per_diver: MoneyResponse,
    pub total_cost_per_diver: MoneyResponse,
    pub total_charge_per_diver: MoneyResponse,
    pub margin_per_diver: MoneyResponse,
    pub diver_count: i32,
}

/// Generic pricing error response
#[derive(Debug, Serialize)]
pub struct PricingErrorResponse {
    pub error_type: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<serde_json::Value>,
}
