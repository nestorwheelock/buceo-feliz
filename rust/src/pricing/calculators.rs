//! Core pricing calculation functions.
//!
//! Pure functions for pricing math - no database access.
//! These mirror the Python implementations in diveops/operations/pricing/calculators.py

use rust_decimal::Decimal;
use rust_decimal::prelude::*;

use crate::pricing::responses::MoneyResponse;

/// Round to specified decimal places using banker's rounding (ROUND_HALF_EVEN).
///
/// Banker's rounding rounds to the nearest even number when the value is exactly
/// halfway between two possibilities. This reduces cumulative rounding bias.
///
/// # Examples
/// ```
/// use rust_decimal_macros::dec;
/// use happydiving_web::pricing::round_money;
///
/// assert_eq!(round_money(dec!(2.5), 0), dec!(2));   // rounds to even
/// assert_eq!(round_money(dec!(3.5), 0), dec!(4));   // rounds to even
/// assert_eq!(round_money(dec!(1.234), 2), dec!(1.23));
/// ```
pub fn round_money(amount: Decimal, places: u32) -> Decimal {
    amount.round_dp_with_strategy(places, RoundingStrategy::MidpointNearestEven)
}

/// Allocate shared costs evenly among divers with remainder handling.
///
/// Uses banker's rounding, then distributes any remainder (due to rounding)
/// to the first N divers in 0.01 increments.
///
/// # Arguments
/// * `shared_total` - Total amount to allocate
/// * `diver_count` - Number of divers to split among
/// * `currency` - Currency code (e.g., "MXN")
///
/// # Returns
/// Tuple of (per_diver_amount, list of individual amounts accounting for remainder)
pub fn allocate_shared_costs(
    shared_total: Decimal,
    diver_count: i32,
    currency: &str,
) -> AllocationResult {
    if diver_count <= 0 {
        return AllocationResult {
            per_diver: MoneyResponse {
                amount: Decimal::ZERO,
                currency: currency.to_string(),
            },
            amounts: vec![],
        };
    }

    // Calculate base per-diver amount with banker's rounding
    let per_diver = round_money(shared_total / Decimal::from(diver_count), 2);

    // Calculate actual total after rounding
    let allocated = per_diver * Decimal::from(diver_count);

    // Calculate remainder (can be positive or negative due to rounding)
    let remainder = shared_total - allocated;

    // Build list of per-diver amounts
    let mut amounts: Vec<MoneyResponse> = (0..diver_count)
        .map(|_| MoneyResponse {
            amount: per_diver,
            currency: currency.to_string(),
        })
        .collect();

    // Distribute remainder in 0.01 increments to first N divers
    if remainder != Decimal::ZERO {
        let increment = if remainder > Decimal::ZERO {
            Decimal::new(1, 2) // 0.01
        } else {
            Decimal::new(-1, 2) // -0.01
        };

        let adjustments_needed = (remainder.abs() / Decimal::new(1, 2))
            .to_i32()
            .unwrap_or(0) as usize;

        for i in 0..adjustments_needed.min(amounts.len()) {
            amounts[i].amount += increment;
        }
    }

    AllocationResult {
        per_diver: MoneyResponse {
            amount: per_diver,
            currency: currency.to_string(),
        },
        amounts,
    }
}

/// Result of shared cost allocation
#[derive(Debug, Clone)]
pub struct AllocationResult {
    pub per_diver: MoneyResponse,
    pub amounts: Vec<MoneyResponse>,
}

/// Calculate pricing totals from lines.
///
/// Aggregates shared and per-diver costs/charges, calculates per-diver shares,
/// and computes margin.
pub fn calculate_totals(
    lines: &[PricingLineInput],
    diver_count: i32,
    currency: &str,
    equipment_rentals: Option<&[EquipmentRentalInput]>,
) -> PricingTotalsResult {
    let mut shared_cost = Decimal::ZERO;
    let mut shared_charge = Decimal::ZERO;
    let mut per_diver_cost = Decimal::ZERO;
    let mut per_diver_charge = Decimal::ZERO;

    for line in lines {
        match line.allocation.as_str() {
            "shared" => {
                shared_cost += line.shop_cost_amount;
                shared_charge += line.customer_charge_amount;
            }
            "per_diver" => {
                per_diver_cost += line.shop_cost_amount;
                per_diver_charge += line.customer_charge_amount;
            }
            _ => {}
        }
    }

    // Add equipment rentals to per-diver totals
    if let Some(rentals) = equipment_rentals {
        for rental in rentals {
            per_diver_cost += rental.unit_cost_amount * Decimal::from(rental.quantity);
            per_diver_charge += rental.unit_charge_amount * Decimal::from(rental.quantity);
        }
    }

    // Calculate per-diver share of shared costs
    let (shared_cost_per_diver, shared_charge_per_diver) = if diver_count > 0 {
        (
            round_money(shared_cost / Decimal::from(diver_count), 2),
            round_money(shared_charge / Decimal::from(diver_count), 2),
        )
    } else {
        (Decimal::ZERO, Decimal::ZERO)
    };

    // Calculate totals per diver
    let total_cost_per_diver = shared_cost_per_diver + per_diver_cost;
    let total_charge_per_diver = shared_charge_per_diver + per_diver_charge;
    let margin_per_diver = total_charge_per_diver - total_cost_per_diver;

    PricingTotalsResult {
        shared_cost: MoneyResponse {
            amount: shared_cost,
            currency: currency.to_string(),
        },
        shared_charge: MoneyResponse {
            amount: shared_charge,
            currency: currency.to_string(),
        },
        per_diver_cost: MoneyResponse {
            amount: per_diver_cost,
            currency: currency.to_string(),
        },
        per_diver_charge: MoneyResponse {
            amount: per_diver_charge,
            currency: currency.to_string(),
        },
        shared_cost_per_diver: MoneyResponse {
            amount: shared_cost_per_diver,
            currency: currency.to_string(),
        },
        shared_charge_per_diver: MoneyResponse {
            amount: shared_charge_per_diver,
            currency: currency.to_string(),
        },
        total_cost_per_diver: MoneyResponse {
            amount: total_cost_per_diver,
            currency: currency.to_string(),
        },
        total_charge_per_diver: MoneyResponse {
            amount: total_charge_per_diver,
            currency: currency.to_string(),
        },
        margin_per_diver: MoneyResponse {
            amount: margin_per_diver,
            currency: currency.to_string(),
        },
        diver_count,
    }
}

/// Input for a pricing line (used in calculate_totals)
#[derive(Debug, Clone)]
pub struct PricingLineInput {
    pub key: String,
    pub allocation: String, // "shared" or "per_diver"
    pub shop_cost_amount: Decimal,
    pub customer_charge_amount: Decimal,
}

/// Input for equipment rental (used in calculate_totals)
#[derive(Debug, Clone)]
pub struct EquipmentRentalInput {
    pub unit_cost_amount: Decimal,
    pub unit_charge_amount: Decimal,
    pub quantity: i32,
}

/// Result of pricing totals calculation
#[derive(Debug, Clone)]
pub struct PricingTotalsResult {
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

#[cfg(test)]
mod tests {
    use super::*;
    use rust_decimal_macros::dec;

    // ==================== round_money tests ====================

    #[test]
    fn test_round_money_bankers_rounding_to_even() {
        // Banker's rounding: 0.5 rounds to nearest even
        assert_eq!(round_money(dec!(2.5), 0), dec!(2)); // rounds down to even
        assert_eq!(round_money(dec!(3.5), 0), dec!(4)); // rounds up to even
        assert_eq!(round_money(dec!(4.5), 0), dec!(4)); // rounds down to even
        assert_eq!(round_money(dec!(5.5), 0), dec!(6)); // rounds up to even
    }

    #[test]
    fn test_round_money_bankers_rounding_decimal_places() {
        assert_eq!(round_money(dec!(2.25), 1), dec!(2.2)); // rounds to even
        assert_eq!(round_money(dec!(2.35), 1), dec!(2.4)); // rounds to even
        assert_eq!(round_money(dec!(2.45), 1), dec!(2.4)); // rounds to even
        assert_eq!(round_money(dec!(2.55), 1), dec!(2.6)); // rounds to even
    }

    #[test]
    fn test_round_money_normal_rounding() {
        // Non-halfway values round normally
        assert_eq!(round_money(dec!(1.234), 2), dec!(1.23));
        assert_eq!(round_money(dec!(1.236), 2), dec!(1.24));
        assert_eq!(round_money(dec!(1.2349), 2), dec!(1.23));
        assert_eq!(round_money(dec!(1.2351), 2), dec!(1.24));
    }

    #[test]
    fn test_round_money_zero() {
        assert_eq!(round_money(dec!(0), 2), dec!(0));
        assert_eq!(round_money(dec!(0.00), 2), dec!(0.00));
    }

    #[test]
    fn test_round_money_negative() {
        assert_eq!(round_money(dec!(-2.5), 0), dec!(-2)); // rounds to even
        assert_eq!(round_money(dec!(-3.5), 0), dec!(-4)); // rounds to even
        assert_eq!(round_money(dec!(-1.234), 2), dec!(-1.23));
    }

    #[test]
    fn test_round_money_large_values() {
        assert_eq!(round_money(dec!(123456.789), 2), dec!(123456.79));
        assert_eq!(round_money(dec!(999999.995), 2), dec!(1000000.00));
    }

    // ==================== allocate_shared_costs tests ====================

    #[test]
    fn test_allocate_shared_costs_even_split() {
        let result = allocate_shared_costs(dec!(100), 4, "MXN");
        assert_eq!(result.per_diver.amount, dec!(25));
        assert_eq!(result.amounts.len(), 4);
        for amount in &result.amounts {
            assert_eq!(amount.amount, dec!(25));
            assert_eq!(amount.currency, "MXN");
        }
    }

    #[test]
    fn test_allocate_shared_costs_with_remainder() {
        let result = allocate_shared_costs(dec!(100), 3, "MXN");
        assert_eq!(result.per_diver.amount, dec!(33.33));

        // Verify total equals original (remainder distributed)
        let total: Decimal = result.amounts.iter().map(|m| m.amount).sum();
        assert_eq!(total, dec!(100));

        // First diver gets the extra penny
        assert_eq!(result.amounts[0].amount, dec!(33.34));
        assert_eq!(result.amounts[1].amount, dec!(33.33));
        assert_eq!(result.amounts[2].amount, dec!(33.33));
    }

    #[test]
    fn test_allocate_shared_costs_zero_divers() {
        let result = allocate_shared_costs(dec!(100), 0, "MXN");
        assert_eq!(result.per_diver.amount, dec!(0));
        assert!(result.amounts.is_empty());
    }

    #[test]
    fn test_allocate_shared_costs_negative_divers() {
        let result = allocate_shared_costs(dec!(100), -1, "MXN");
        assert_eq!(result.per_diver.amount, dec!(0));
        assert!(result.amounts.is_empty());
    }

    #[test]
    fn test_allocate_shared_costs_single_diver() {
        let result = allocate_shared_costs(dec!(100), 1, "MXN");
        assert_eq!(result.per_diver.amount, dec!(100));
        assert_eq!(result.amounts.len(), 1);
        assert_eq!(result.amounts[0].amount, dec!(100));
    }

    #[test]
    fn test_allocate_shared_costs_large_remainder() {
        // 100 / 7 = 14.285714... rounds to 14.29
        // 14.29 * 7 = 100.03, so remainder is -0.03
        let result = allocate_shared_costs(dec!(100), 7, "MXN");

        // Verify total equals original
        let total: Decimal = result.amounts.iter().map(|m| m.amount).sum();
        assert_eq!(total, dec!(100));
    }

    // ==================== calculate_totals tests ====================

    #[test]
    fn test_calculate_totals_shared_only() {
        let lines = vec![PricingLineInput {
            key: "boat".to_string(),
            allocation: "shared".to_string(),
            shop_cost_amount: dec!(1000),
            customer_charge_amount: dec!(1200),
        }];

        let totals = calculate_totals(&lines, 4, "MXN", None);

        assert_eq!(totals.shared_cost.amount, dec!(1000));
        assert_eq!(totals.shared_charge.amount, dec!(1200));
        assert_eq!(totals.shared_cost_per_diver.amount, dec!(250));
        assert_eq!(totals.shared_charge_per_diver.amount, dec!(300));
        assert_eq!(totals.per_diver_cost.amount, dec!(0));
        assert_eq!(totals.per_diver_charge.amount, dec!(0));
        assert_eq!(totals.total_cost_per_diver.amount, dec!(250));
        assert_eq!(totals.total_charge_per_diver.amount, dec!(300));
        assert_eq!(totals.margin_per_diver.amount, dec!(50));
    }

    #[test]
    fn test_calculate_totals_per_diver_only() {
        let lines = vec![PricingLineInput {
            key: "gas".to_string(),
            allocation: "per_diver".to_string(),
            shop_cost_amount: dec!(50),
            customer_charge_amount: dec!(0),
        }];

        let totals = calculate_totals(&lines, 4, "MXN", None);

        assert_eq!(totals.shared_cost.amount, dec!(0));
        assert_eq!(totals.per_diver_cost.amount, dec!(50));
        assert_eq!(totals.total_cost_per_diver.amount, dec!(50));
        assert_eq!(totals.margin_per_diver.amount, dec!(-50)); // negative margin
    }

    #[test]
    fn test_calculate_totals_mixed() {
        let lines = vec![
            PricingLineInput {
                key: "boat".to_string(),
                allocation: "shared".to_string(),
                shop_cost_amount: dec!(1000),
                customer_charge_amount: dec!(1200),
            },
            PricingLineInput {
                key: "gas".to_string(),
                allocation: "per_diver".to_string(),
                shop_cost_amount: dec!(50),
                customer_charge_amount: dec!(0),
            },
        ];

        let totals = calculate_totals(&lines, 4, "MXN", None);

        assert_eq!(totals.shared_cost.amount, dec!(1000));
        assert_eq!(totals.shared_cost_per_diver.amount, dec!(250));
        assert_eq!(totals.per_diver_cost.amount, dec!(50));
        assert_eq!(totals.total_cost_per_diver.amount, dec!(300)); // 250 + 50
        assert_eq!(totals.total_charge_per_diver.amount, dec!(300)); // 300 + 0
    }

    #[test]
    fn test_calculate_totals_with_equipment() {
        let lines = vec![PricingLineInput {
            key: "boat".to_string(),
            allocation: "shared".to_string(),
            shop_cost_amount: dec!(1000),
            customer_charge_amount: dec!(1200),
        }];

        let rentals = vec![EquipmentRentalInput {
            unit_cost_amount: dec!(10),
            unit_charge_amount: dec!(25),
            quantity: 2,
        }];

        let totals = calculate_totals(&lines, 4, "MXN", Some(&rentals));

        // Equipment: cost = 10*2 = 20, charge = 25*2 = 50
        assert_eq!(totals.per_diver_cost.amount, dec!(20));
        assert_eq!(totals.per_diver_charge.amount, dec!(50));
        assert_eq!(totals.total_cost_per_diver.amount, dec!(270)); // 250 + 20
        assert_eq!(totals.total_charge_per_diver.amount, dec!(350)); // 300 + 50
    }

    #[test]
    fn test_calculate_totals_zero_divers() {
        let lines = vec![PricingLineInput {
            key: "boat".to_string(),
            allocation: "shared".to_string(),
            shop_cost_amount: dec!(1000),
            customer_charge_amount: dec!(1200),
        }];

        let totals = calculate_totals(&lines, 0, "MXN", None);

        assert_eq!(totals.shared_cost_per_diver.amount, dec!(0));
        assert_eq!(totals.shared_charge_per_diver.amount, dec!(0));
        assert_eq!(totals.diver_count, 0);
    }
}
