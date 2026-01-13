//! Database models for pricing queries.
//!
//! These models use sqlx's FromRow derive for direct database deserialization.

use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;

/// Agreement from django_agreements_agreement
#[derive(Debug, Clone, FromRow)]
pub struct Agreement {
    pub id: Uuid,
    pub party_a_content_type_id: Option<i32>,
    pub party_a_id: String,
    pub party_b_content_type_id: Option<i32>,
    pub party_b_id: String,
    pub scope_type: String,
    pub scope_ref_content_type_id: Option<i32>,
    pub scope_ref_id: String,
    pub terms: serde_json::Value,
    pub valid_from: DateTime<Utc>,
    pub valid_to: Option<DateTime<Utc>>,
    pub current_version: i32,
    pub deleted_at: Option<DateTime<Utc>>,
}

impl Agreement {
    /// Check if agreement is valid at the given time
    pub fn is_valid_at(&self, check_time: DateTime<Utc>) -> bool {
        if self.deleted_at.is_some() {
            return false;
        }
        if self.valid_from > check_time {
            return false;
        }
        match self.valid_to {
            Some(end) => check_time < end,
            None => true,
        }
    }
}

/// Price from pricing_price
#[derive(Debug, Clone, FromRow)]
pub struct Price {
    pub id: Uuid,
    pub catalog_item_id: Uuid,
    pub amount: Decimal,
    pub currency: String,
    pub cost_amount: Option<Decimal>,
    pub cost_currency: Option<String>,
    pub organization_id: Option<Uuid>,
    pub party_id: Option<Uuid>,
    pub agreement_id: Option<Uuid>,
    pub valid_from: DateTime<Utc>,
    pub valid_to: Option<DateTime<Utc>>,
    pub priority: i32,
}

/// CatalogItem from django_catalog_catalogitem
#[derive(Debug, Clone, FromRow)]
pub struct CatalogItem {
    pub id: Uuid,
    pub display_name: String,
    pub active: bool,
    pub deleted_at: Option<DateTime<Utc>>,
}

/// DiveSite from diveops_operations_divesite
#[derive(Debug, Clone, FromRow)]
pub struct DiveSite {
    pub id: Uuid,
    pub name: String,
    pub deleted_at: Option<DateTime<Utc>>,
}

/// Organization from django_parties_organization
#[derive(Debug, Clone, FromRow)]
pub struct Organization {
    pub id: Uuid,
    pub name: String,
    pub deleted_at: Option<DateTime<Utc>>,
}

/// ContentType from django_content_type (for GenericFK resolution)
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct ContentType {
    pub id: i32,
    pub app_label: String,
    pub model: String,
}
