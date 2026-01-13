//! Pricing engine module for diveops.
//!
//! Provides high-performance pricing calculations for dive excursions.
//! This module is called by Django via HTTP/JSON for pricing operations.

pub mod calculators;
pub mod models;
pub mod queries;
pub mod requests;
pub mod responses;
pub mod routes;
pub mod services;

// Re-export commonly used items
pub use calculators::round_money;
pub use routes::router;
pub use services::{BoatCostResult, GasFillResult, ComponentPricingResult, PricingError};
