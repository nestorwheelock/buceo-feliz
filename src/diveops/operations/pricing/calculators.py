"""Pricing calculators for diveops.

Functions to calculate costs from primitive data sources
(Agreement terms, Price rules, etc.)

When USE_RUST_PRICING is enabled, calculations are delegated to the
high-performance Rust service for improved performance.
"""

import logging
from decimal import Decimal, ROUND_HALF_EVEN
from typing import NamedTuple

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from django_agreements.models import Agreement
from django_money import Money

from .exceptions import (
    MissingVendorAgreementError,
    MissingPriceError,
    CurrencyMismatchError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)


class BoatCostResult(NamedTuple):
    """Result of boat cost calculation."""

    total: Money
    per_diver: Money
    base_cost: Money
    overage_count: int
    overage_per_diver: Money
    included_divers: int
    diver_count: int
    agreement_id: str | None


class GasFillResult(NamedTuple):
    """Result of gas fill pricing."""

    cost_per_fill: Money
    charge_per_fill: Money
    total_cost: Money
    total_charge: Money
    fills_count: int
    gas_type: str
    agreement_id: str | None
    price_rule_id: str | None


def round_money(amount: Decimal, places: int = 2) -> Decimal:
    """Round to specified decimal places using banker's rounding."""
    quantize_str = "0." + "0" * places
    return amount.quantize(Decimal(quantize_str), rounding=ROUND_HALF_EVEN)


def calculate_boat_cost(
    dive_site,
    diver_count: int,
    as_of=None,
) -> BoatCostResult:
    """Calculate boat cost using tiered pricing from vendor agreement.

    Looks up the vendor agreement for the given dive site and calculates
    the total and per-diver boat cost based on the tier structure.

    When USE_RUST_PRICING is enabled, delegates to the Rust pricing service.

    Args:
        dive_site: DiveSite instance
        diver_count: Number of divers on the excursion
        as_of: Point in time for pricing (default: now)

    Returns:
        BoatCostResult with breakdown

    Raises:
        MissingVendorAgreementError: No agreement found for site
        ConfigurationError: Agreement terms missing required fields
    """
    # Delegate to Rust if enabled
    if getattr(settings, "USE_RUST_PRICING", False):
        try:
            from . import rust_client

            as_of_str = as_of.isoformat() if as_of else None
            result = rust_client.calculate_boat_cost(
                dive_site_id=dive_site.pk,
                diver_count=diver_count,
                as_of=as_of_str,
            )
            return BoatCostResult(
                total=Money(result.total_amount, result.total_currency),
                per_diver=Money(result.per_diver_amount, result.per_diver_currency),
                base_cost=Money(result.base_cost_amount, result.base_cost_currency),
                overage_count=result.overage_count,
                overage_per_diver=Money(result.overage_per_diver_amount, result.overage_per_diver_currency),
                included_divers=result.included_divers,
                diver_count=result.diver_count,
                agreement_id=str(result.agreement_id) if result.agreement_id else None,
            )
        except rust_client.RustPricingUnavailable:
            logger.warning("Rust pricing unavailable, falling back to Python")
        except rust_client.RustPricingError as e:
            if e.error_type == "missing_vendor_agreement":
                raise MissingVendorAgreementError(
                    scope_type="vendor_pricing",
                    scope_ref=f"DiveSite:{dive_site.pk}",
                ) from e
            elif e.error_type == "configuration_error":
                raise ConfigurationError(e.message) from e
            raise

    if diver_count <= 0:
        raise ConfigurationError("Diver count must be positive")

    check_time = as_of or timezone.now()

    # Find active vendor agreement for this site
    site_content_type = ContentType.objects.get_for_model(dive_site)
    agreement = (
        Agreement.objects.filter(
            scope_type="vendor_pricing",
            scope_ref_content_type=site_content_type,
            scope_ref_id=str(dive_site.pk),
        )
        .as_of(check_time)
        .first()
    )

    if not agreement:
        # Fall back to dive_shop-level agreement (no site scope)
        if hasattr(dive_site, "excursion_types") and dive_site.excursion_types.exists():
            # Try to find from excursion type's dive shop
            pass  # For now, require site-specific agreement

        raise MissingVendorAgreementError(
            scope_type="vendor_pricing",
            scope_ref=f"DiveSite:{dive_site.pk}",
        )

    # Extract boat tier from agreement terms
    boat_tier = agreement.terms.get("boat_charter")
    if not boat_tier:
        raise ConfigurationError(
            f"Agreement {agreement.pk} missing 'boat_charter' in terms",
            errors=["boat_charter not in agreement.terms"],
        )

    # Parse tier structure
    try:
        base_cost = Decimal(str(boat_tier.get("base_cost", "0")))
        included_divers = int(boat_tier.get("included_divers", 4))
        overage_per_diver = Decimal(str(boat_tier.get("overage_per_diver", "0")))
        currency = boat_tier.get("currency", "MXN")
    except (ValueError, TypeError) as e:
        raise ConfigurationError(
            f"Invalid boat_charter values in agreement {agreement.pk}: {e}"
        )

    # Calculate total boat cost
    if diver_count <= included_divers:
        total_amount = base_cost
        overage_count = 0
    else:
        overage_count = diver_count - included_divers
        total_amount = base_cost + (overage_count * overage_per_diver)

    # Calculate per-diver share (banker's rounding)
    per_diver_amount = round_money(total_amount / diver_count)

    return BoatCostResult(
        total=Money(total_amount, currency),
        per_diver=Money(per_diver_amount, currency),
        base_cost=Money(base_cost, currency),
        overage_count=overage_count,
        overage_per_diver=Money(overage_per_diver, currency),
        included_divers=included_divers,
        diver_count=diver_count,
        agreement_id=str(agreement.pk),
    )


def calculate_gas_fills(
    dive_shop,
    gas_type: str,
    fills_count: int,
    customer_charge_amount: Decimal | None = None,
    as_of=None,
) -> GasFillResult:
    """Calculate gas fill costs from vendor agreement.

    When USE_RUST_PRICING is enabled, delegates to the Rust pricing service.

    Args:
        dive_shop: Organization (dive shop)
        gas_type: Type of gas (air, ean32, ean36, trimix)
        fills_count: Number of tank fills
        customer_charge_amount: Optional override for customer charge (e.g., included in package)
        as_of: Point in time for pricing (default: now)

    Returns:
        GasFillResult with cost and charge breakdown

    Raises:
        MissingVendorAgreementError: No gas vendor agreement found
        ConfigurationError: Agreement terms missing gas pricing
    """
    # Delegate to Rust if enabled
    if getattr(settings, "USE_RUST_PRICING", False):
        try:
            from . import rust_client

            as_of_str = as_of.isoformat() if as_of else None
            result = rust_client.calculate_gas_fills(
                dive_shop_id=dive_shop.pk,
                gas_type=gas_type,
                fills_count=fills_count,
                customer_charge_override=customer_charge_amount,
                as_of=as_of_str,
            )
            return GasFillResult(
                cost_per_fill=Money(result.cost_per_fill_amount, result.cost_per_fill_currency),
                charge_per_fill=Money(result.charge_per_fill_amount, result.charge_per_fill_currency),
                total_cost=Money(result.total_cost_amount, result.total_cost_currency),
                total_charge=Money(result.total_charge_amount, result.total_charge_currency),
                fills_count=result.fills_count,
                gas_type=result.gas_type,
                agreement_id=str(result.agreement_id) if result.agreement_id else None,
                price_rule_id=str(result.price_rule_id) if result.price_rule_id else None,
            )
        except rust_client.RustPricingUnavailable:
            logger.warning("Rust pricing unavailable, falling back to Python")
        except rust_client.RustPricingError as e:
            if e.error_type == "missing_vendor_agreement":
                raise MissingVendorAgreementError(
                    scope_type="gas_vendor_pricing",
                    scope_ref=f"Organization:{dive_shop.pk}",
                ) from e
            elif e.error_type == "configuration_error":
                raise ConfigurationError(e.message) from e
            raise

    if fills_count <= 0:
        raise ConfigurationError("Fills count must be positive")

    check_time = as_of or timezone.now()

    # Find active gas vendor agreement for dive shop
    shop_content_type = ContentType.objects.get_for_model(dive_shop)
    agreement = (
        Agreement.objects.filter(
            scope_type="gas_vendor_pricing",
            party_a_content_type=shop_content_type,
            party_a_id=str(dive_shop.pk),
        )
        .as_of(check_time)
        .first()
    )

    if not agreement:
        raise MissingVendorAgreementError(
            scope_type="gas_vendor_pricing",
            scope_ref=f"Organization:{dive_shop.pk}",
        )

    # Extract gas pricing from agreement terms
    gas_fills = agreement.terms.get("gas_fills", {})
    gas_pricing = gas_fills.get(gas_type.lower())

    if not gas_pricing:
        raise ConfigurationError(
            f"Agreement {agreement.pk} missing pricing for gas type '{gas_type}'",
            errors=[f"gas_fills.{gas_type} not in agreement.terms"],
        )

    # Parse pricing
    try:
        cost_per_fill = Decimal(str(gas_pricing.get("cost", "0")))
        currency = gas_pricing.get("currency", "MXN")
    except (ValueError, TypeError) as e:
        raise ConfigurationError(
            f"Invalid gas pricing values in agreement {agreement.pk}: {e}"
        )

    # Customer charge - use override if provided, else from agreement
    if customer_charge_amount is not None:
        charge_per_fill = customer_charge_amount
    else:
        charge_per_fill = Decimal(str(gas_pricing.get("charge", "0")))

    # Calculate totals
    total_cost = cost_per_fill * fills_count
    total_charge = charge_per_fill * fills_count

    return GasFillResult(
        cost_per_fill=Money(cost_per_fill, currency),
        charge_per_fill=Money(charge_per_fill, currency),
        total_cost=Money(total_cost, currency),
        total_charge=Money(total_charge, currency),
        fills_count=fills_count,
        gas_type=gas_type,
        agreement_id=str(agreement.pk),
        price_rule_id=None,  # Could be populated if using Price model
    )


def resolve_component_pricing(
    catalog_item,
    dive_shop=None,
    party=None,
    agreement=None,
    as_of=None,
):
    """Resolve pricing for a catalog item component.

    Uses the Price model's resolution hierarchy:
    1. Agreement-specific
    2. Party-specific
    3. Organization-specific
    4. Global

    When USE_RUST_PRICING is enabled, delegates to the Rust pricing service.

    Args:
        catalog_item: CatalogItem to price
        dive_shop: Organization for org-scoped pricing
        party: Person for party-scoped pricing
        agreement: Agreement for agreement-scoped pricing
        as_of: Point in time for pricing

    Returns:
        dict with cost, charge, price_rule_id, vendor_agreement_id
    """
    # Delegate to Rust if enabled
    if getattr(settings, "USE_RUST_PRICING", False):
        try:
            from . import rust_client

            as_of_str = as_of.isoformat() if as_of else None
            result = rust_client.resolve_component_pricing(
                catalog_item_id=catalog_item.pk,
                dive_shop_id=dive_shop.pk if dive_shop else None,
                party_id=party.pk if party else None,
                agreement_id=agreement.pk if agreement else None,
                as_of=as_of_str,
            )
            return {
                "charge_amount": result.charge_amount,
                "charge_currency": result.charge_currency,
                "cost_amount": result.cost_amount,
                "cost_currency": result.cost_currency,
                "price_rule_id": str(result.price_rule_id),
                "has_cost": result.has_cost,
            }
        except rust_client.RustPricingUnavailable:
            logger.warning("Rust pricing unavailable, falling back to Python")
        except rust_client.RustPricingError as e:
            if e.error_type == "missing_price":
                raise MissingPriceError(
                    catalog_item_id=str(catalog_item.pk),
                    context=catalog_item.display_name,
                ) from e
            raise

    from diveops.pricing.models import Price

    check_time = as_of or timezone.now()

    # Build price query with resolution hierarchy
    base_qs = Price.objects.filter(catalog_item=catalog_item).current(as_of=check_time)

    # Try resolution in priority order
    price = None

    if agreement:
        price = base_qs.filter(agreement=agreement).order_by("-priority", "-valid_from").first()

    if not price and party:
        price = base_qs.filter(
            party=party,
            agreement__isnull=True,
        ).order_by("-priority", "-valid_from").first()

    if not price and dive_shop:
        price = base_qs.filter(
            organization=dive_shop,
            party__isnull=True,
            agreement__isnull=True,
        ).order_by("-priority", "-valid_from").first()

    if not price:
        price = base_qs.global_scope().order_by("-priority", "-valid_from").first()

    if not price:
        raise MissingPriceError(
            catalog_item_id=str(catalog_item.pk),
            context=catalog_item.display_name,
        )

    return {
        "charge_amount": price.amount,
        "charge_currency": price.currency,
        "cost_amount": price.cost_amount,
        "cost_currency": price.cost_currency or price.currency,
        "price_rule_id": str(price.pk),
        "has_cost": price.has_cost,
    }


def allocate_shared_costs(
    shared_total: Decimal,
    diver_count: int,
    currency: str = "MXN",
) -> tuple[Decimal, list[Decimal]]:
    """Allocate shared costs evenly among divers with remainder handling.

    Uses banker's rounding, then distributes any remainder (due to rounding)
    to the first N divers.

    When USE_RUST_PRICING is enabled, delegates to the Rust pricing service.

    Args:
        shared_total: Total amount to allocate
        diver_count: Number of divers to split among
        currency: Currency code (for Money object)

    Returns:
        Tuple of (per_diver_amount, list of per-diver amounts)
        The list handles remainder distribution.

    Example:
        allocate_shared_costs(Decimal("100"), 3)
        # Returns (Decimal("33.33"), [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")])
    """
    # Delegate to Rust if enabled
    if getattr(settings, "USE_RUST_PRICING", False):
        try:
            from . import rust_client

            return rust_client.allocate_shared_costs(
                shared_total=shared_total,
                diver_count=diver_count,
                currency=currency,
            )
        except rust_client.RustPricingUnavailable:
            logger.warning("Rust pricing unavailable, falling back to Python")
        except rust_client.RustPricingError:
            logger.warning("Rust pricing error, falling back to Python")

    if diver_count <= 0:
        return Decimal("0"), []

    # Calculate base per-diver amount (rounded down to avoid overallocation)
    per_diver = round_money(shared_total / diver_count)

    # Calculate actual total after rounding
    allocated = per_diver * diver_count

    # Calculate remainder (can be positive or negative due to rounding)
    remainder = shared_total - allocated

    # Build list of per-diver amounts
    amounts = [per_diver] * diver_count

    # Distribute remainder in 0.01 increments to first N divers
    if remainder != 0:
        increment = Decimal("0.01") if remainder > 0 else Decimal("-0.01")
        adjustments_needed = abs(int(remainder / Decimal("0.01")))

        for i in range(min(adjustments_needed, diver_count)):
            amounts[i] += increment

    return per_diver, amounts
