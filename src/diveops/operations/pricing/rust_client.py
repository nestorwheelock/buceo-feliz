"""HTTP client for Rust pricing engine.

This module provides sync and async clients for calling the Rust pricing
service. When USE_RUST_PRICING is enabled, pricing calculations are
delegated to the high-performance Rust implementation.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class RustPricingError(Exception):
    """Error from Rust pricing service."""

    def __init__(self, error_type: str, message: str, details: dict | None = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)


class RustPricingUnavailable(Exception):
    """Rust pricing service is unavailable."""

    pass


@dataclass
class BoatCostResult:
    """Result from boat cost calculation."""

    total_amount: Decimal
    total_currency: str
    per_diver_amount: Decimal
    per_diver_currency: str
    base_cost_amount: Decimal
    base_cost_currency: str
    overage_count: int
    overage_per_diver_amount: Decimal
    overage_per_diver_currency: str
    included_divers: int
    diver_count: int
    agreement_id: UUID | None


@dataclass
class GasFillResult:
    """Result from gas fill calculation."""

    cost_per_fill_amount: Decimal
    cost_per_fill_currency: str
    charge_per_fill_amount: Decimal
    charge_per_fill_currency: str
    total_cost_amount: Decimal
    total_cost_currency: str
    total_charge_amount: Decimal
    total_charge_currency: str
    fills_count: int
    gas_type: str
    agreement_id: UUID | None
    price_rule_id: UUID | None


@dataclass
class ComponentPricingResult:
    """Result from component pricing resolution."""

    charge_amount: Decimal
    charge_currency: str
    cost_amount: Decimal | None
    cost_currency: str
    price_rule_id: UUID
    has_cost: bool


def _get_client() -> httpx.Client:
    """Get a configured httpx client."""
    return httpx.Client(
        base_url=settings.RUST_PRICING_URL,
        timeout=settings.RUST_PRICING_TIMEOUT,
    )


def _get_async_client() -> httpx.AsyncClient:
    """Get a configured async httpx client."""
    return httpx.AsyncClient(
        base_url=settings.RUST_PRICING_URL,
        timeout=settings.RUST_PRICING_TIMEOUT,
    )


def _handle_response(response: httpx.Response) -> dict:
    """Handle response from Rust service."""
    if response.status_code == 200:
        return response.json()

    # Handle error responses
    try:
        error_data = response.json()
        raise RustPricingError(
            error_type=error_data.get("error_type", "unknown"),
            message=error_data.get("message", "Unknown error"),
            details=error_data.get("details"),
        )
    except (ValueError, KeyError):
        response.raise_for_status()


def check_health() -> bool:
    """Check if Rust pricing service is healthy.

    Returns:
        True if service is healthy, False otherwise.
    """
    try:
        with _get_client() as client:
            response = client.get("/health")
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "ok"
            return False
    except httpx.RequestError as e:
        logger.warning("Rust pricing health check failed: %s", e)
        return False


def calculate_boat_cost(
    dive_site_id: UUID,
    diver_count: int,
    as_of: str | None = None,
) -> BoatCostResult:
    """Calculate boat cost using Rust pricing engine.

    Args:
        dive_site_id: UUID of the dive site
        diver_count: Number of divers
        as_of: Optional ISO timestamp for pricing lookup

    Returns:
        BoatCostResult with breakdown

    Raises:
        RustPricingError: On pricing calculation error
        RustPricingUnavailable: If service is unavailable
    """
    payload: dict[str, Any] = {
        "dive_site_id": str(dive_site_id),
        "diver_count": diver_count,
    }
    if as_of:
        payload["as_of"] = as_of

    try:
        with _get_client() as client:
            response = client.post("/boat-cost", json=payload)
            data = _handle_response(response)
    except httpx.RequestError as e:
        logger.error("Rust pricing service unavailable: %s", e)
        raise RustPricingUnavailable(str(e)) from e

    return BoatCostResult(
        total_amount=Decimal(data["total"]["amount"]),
        total_currency=data["total"]["currency"],
        per_diver_amount=Decimal(data["per_diver"]["amount"]),
        per_diver_currency=data["per_diver"]["currency"],
        base_cost_amount=Decimal(data["base_cost"]["amount"]),
        base_cost_currency=data["base_cost"]["currency"],
        overage_count=data["overage_count"],
        overage_per_diver_amount=Decimal(data["overage_per_diver"]["amount"]),
        overage_per_diver_currency=data["overage_per_diver"]["currency"],
        included_divers=data["included_divers"],
        diver_count=data["diver_count"],
        agreement_id=UUID(data["agreement_id"]) if data.get("agreement_id") else None,
    )


def calculate_gas_fills(
    dive_shop_id: UUID,
    gas_type: str,
    fills_count: int,
    customer_charge_override: Decimal | None = None,
    as_of: str | None = None,
) -> GasFillResult:
    """Calculate gas fill costs using Rust pricing engine.

    Args:
        dive_shop_id: UUID of the dive shop (Organization)
        gas_type: Type of gas (air, ean32, ean36, etc.)
        fills_count: Number of tank fills
        customer_charge_override: Optional override for customer charge
        as_of: Optional ISO timestamp for pricing lookup

    Returns:
        GasFillResult with breakdown

    Raises:
        RustPricingError: On pricing calculation error
        RustPricingUnavailable: If service is unavailable
    """
    payload: dict[str, Any] = {
        "dive_shop_id": str(dive_shop_id),
        "gas_type": gas_type,
        "fills_count": fills_count,
    }
    if customer_charge_override is not None:
        payload["customer_charge_override"] = str(customer_charge_override)
    if as_of:
        payload["as_of"] = as_of

    try:
        with _get_client() as client:
            response = client.post("/gas-fills", json=payload)
            data = _handle_response(response)
    except httpx.RequestError as e:
        logger.error("Rust pricing service unavailable: %s", e)
        raise RustPricingUnavailable(str(e)) from e

    return GasFillResult(
        cost_per_fill_amount=Decimal(data["cost_per_fill"]["amount"]),
        cost_per_fill_currency=data["cost_per_fill"]["currency"],
        charge_per_fill_amount=Decimal(data["charge_per_fill"]["amount"]),
        charge_per_fill_currency=data["charge_per_fill"]["currency"],
        total_cost_amount=Decimal(data["total_cost"]["amount"]),
        total_cost_currency=data["total_cost"]["currency"],
        total_charge_amount=Decimal(data["total_charge"]["amount"]),
        total_charge_currency=data["total_charge"]["currency"],
        fills_count=data["fills_count"],
        gas_type=data["gas_type"],
        agreement_id=UUID(data["agreement_id"]) if data.get("agreement_id") else None,
        price_rule_id=UUID(data["price_rule_id"]) if data.get("price_rule_id") else None,
    )


def resolve_component_pricing(
    catalog_item_id: UUID,
    dive_shop_id: UUID | None = None,
    party_id: UUID | None = None,
    agreement_id: UUID | None = None,
    as_of: str | None = None,
) -> ComponentPricingResult:
    """Resolve component pricing using Rust pricing engine.

    Args:
        catalog_item_id: UUID of the catalog item
        dive_shop_id: Optional organization for org-scoped pricing
        party_id: Optional party for party-scoped pricing
        agreement_id: Optional agreement for agreement-scoped pricing
        as_of: Optional ISO timestamp for pricing lookup

    Returns:
        ComponentPricingResult with pricing info

    Raises:
        RustPricingError: On pricing calculation error
        RustPricingUnavailable: If service is unavailable
    """
    payload: dict[str, Any] = {
        "catalog_item_id": str(catalog_item_id),
    }
    if dive_shop_id:
        payload["dive_shop_id"] = str(dive_shop_id)
    if party_id:
        payload["party_id"] = str(party_id)
    if agreement_id:
        payload["agreement_id"] = str(agreement_id)
    if as_of:
        payload["as_of"] = as_of

    try:
        with _get_client() as client:
            response = client.post("/resolve", json=payload)
            data = _handle_response(response)
    except httpx.RequestError as e:
        logger.error("Rust pricing service unavailable: %s", e)
        raise RustPricingUnavailable(str(e)) from e

    return ComponentPricingResult(
        charge_amount=Decimal(data["charge_amount"]),
        charge_currency=data["charge_currency"],
        cost_amount=Decimal(data["cost_amount"]) if data.get("cost_amount") else None,
        cost_currency=data["cost_currency"],
        price_rule_id=UUID(data["price_rule_id"]),
        has_cost=data["has_cost"],
    )


def allocate_shared_costs(
    shared_total: Decimal,
    diver_count: int,
    currency: str = "MXN",
) -> tuple[Decimal, list[Decimal]]:
    """Allocate shared costs using Rust pricing engine.

    Args:
        shared_total: Total amount to allocate
        diver_count: Number of divers to split among
        currency: Currency code

    Returns:
        Tuple of (per_diver_amount, list of per-diver amounts)

    Raises:
        RustPricingError: On pricing calculation error
        RustPricingUnavailable: If service is unavailable
    """
    payload = {
        "shared_total": str(shared_total),
        "diver_count": diver_count,
        "currency": currency,
    }

    try:
        with _get_client() as client:
            response = client.post("/allocate", json=payload)
            data = _handle_response(response)
    except httpx.RequestError as e:
        logger.error("Rust pricing service unavailable: %s", e)
        raise RustPricingUnavailable(str(e)) from e

    per_diver = Decimal(data["per_diver"]["amount"])
    amounts = [Decimal(m["amount"]) for m in data["amounts"]]

    return per_diver, amounts


def calculate_totals(
    lines: list[dict],
    diver_count: int,
    currency: str = "MXN",
    equipment_rentals: list[dict] | None = None,
) -> dict:
    """Calculate pricing totals using Rust pricing engine.

    Args:
        lines: List of pricing line dicts with key, allocation, shop_cost_amount, etc.
        diver_count: Number of divers
        currency: Currency code
        equipment_rentals: Optional list of equipment rental dicts

    Returns:
        Dict with totals breakdown

    Raises:
        RustPricingError: On pricing calculation error
        RustPricingUnavailable: If service is unavailable
    """
    payload = {
        "lines": lines,
        "diver_count": diver_count,
        "currency": currency,
        "equipment_rentals": equipment_rentals or [],
    }

    try:
        with _get_client() as client:
            response = client.post("/totals", json=payload)
            data = _handle_response(response)
    except httpx.RequestError as e:
        logger.error("Rust pricing service unavailable: %s", e)
        raise RustPricingUnavailable(str(e)) from e

    return {
        "shared_cost": Decimal(data["shared_cost"]["amount"]),
        "shared_charge": Decimal(data["shared_charge"]["amount"]),
        "per_diver_cost": Decimal(data["per_diver_cost"]["amount"]),
        "per_diver_charge": Decimal(data["per_diver_charge"]["amount"]),
        "shared_cost_per_diver": Decimal(data["shared_cost_per_diver"]["amount"]),
        "shared_charge_per_diver": Decimal(data["shared_charge_per_diver"]["amount"]),
        "total_cost_per_diver": Decimal(data["total_cost_per_diver"]["amount"]),
        "total_charge_per_diver": Decimal(data["total_charge_per_diver"]["amount"]),
        "margin_per_diver": Decimal(data["margin_per_diver"]["amount"]),
        "diver_count": data["diver_count"],
        "currency": currency,
    }


# Async versions for use with Django async views


async def async_check_health() -> bool:
    """Async version of check_health."""
    try:
        async with _get_async_client() as client:
            response = await client.get("/health")
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "ok"
            return False
    except httpx.RequestError as e:
        logger.warning("Rust pricing health check failed: %s", e)
        return False


async def async_calculate_boat_cost(
    dive_site_id: UUID,
    diver_count: int,
    as_of: str | None = None,
) -> BoatCostResult:
    """Async version of calculate_boat_cost."""
    payload: dict[str, Any] = {
        "dive_site_id": str(dive_site_id),
        "diver_count": diver_count,
    }
    if as_of:
        payload["as_of"] = as_of

    try:
        async with _get_async_client() as client:
            response = await client.post("/boat-cost", json=payload)
            data = _handle_response(response)
    except httpx.RequestError as e:
        logger.error("Rust pricing service unavailable: %s", e)
        raise RustPricingUnavailable(str(e)) from e

    return BoatCostResult(
        total_amount=Decimal(data["total"]["amount"]),
        total_currency=data["total"]["currency"],
        per_diver_amount=Decimal(data["per_diver"]["amount"]),
        per_diver_currency=data["per_diver"]["currency"],
        base_cost_amount=Decimal(data["base_cost"]["amount"]),
        base_cost_currency=data["base_cost"]["currency"],
        overage_count=data["overage_count"],
        overage_per_diver_amount=Decimal(data["overage_per_diver"]["amount"]),
        overage_per_diver_currency=data["overage_per_diver"]["currency"],
        included_divers=data["included_divers"],
        diver_count=data["diver_count"],
        agreement_id=UUID(data["agreement_id"]) if data.get("agreement_id") else None,
    )


async def async_calculate_gas_fills(
    dive_shop_id: UUID,
    gas_type: str,
    fills_count: int,
    customer_charge_override: Decimal | None = None,
    as_of: str | None = None,
) -> GasFillResult:
    """Async version of calculate_gas_fills."""
    payload: dict[str, Any] = {
        "dive_shop_id": str(dive_shop_id),
        "gas_type": gas_type,
        "fills_count": fills_count,
    }
    if customer_charge_override is not None:
        payload["customer_charge_override"] = str(customer_charge_override)
    if as_of:
        payload["as_of"] = as_of

    try:
        async with _get_async_client() as client:
            response = await client.post("/gas-fills", json=payload)
            data = _handle_response(response)
    except httpx.RequestError as e:
        logger.error("Rust pricing service unavailable: %s", e)
        raise RustPricingUnavailable(str(e)) from e

    return GasFillResult(
        cost_per_fill_amount=Decimal(data["cost_per_fill"]["amount"]),
        cost_per_fill_currency=data["cost_per_fill"]["currency"],
        charge_per_fill_amount=Decimal(data["charge_per_fill"]["amount"]),
        charge_per_fill_currency=data["charge_per_fill"]["currency"],
        total_cost_amount=Decimal(data["total_cost"]["amount"]),
        total_cost_currency=data["total_cost"]["currency"],
        total_charge_amount=Decimal(data["total_charge"]["amount"]),
        total_charge_currency=data["total_charge"]["currency"],
        fills_count=data["fills_count"],
        gas_type=data["gas_type"],
        agreement_id=UUID(data["agreement_id"]) if data.get("agreement_id") else None,
        price_rule_id=UUID(data["price_rule_id"]) if data.get("price_rule_id") else None,
    )


async def async_resolve_component_pricing(
    catalog_item_id: UUID,
    dive_shop_id: UUID | None = None,
    party_id: UUID | None = None,
    agreement_id: UUID | None = None,
    as_of: str | None = None,
) -> ComponentPricingResult:
    """Async version of resolve_component_pricing."""
    payload: dict[str, Any] = {
        "catalog_item_id": str(catalog_item_id),
    }
    if dive_shop_id:
        payload["dive_shop_id"] = str(dive_shop_id)
    if party_id:
        payload["party_id"] = str(party_id)
    if agreement_id:
        payload["agreement_id"] = str(agreement_id)
    if as_of:
        payload["as_of"] = as_of

    try:
        async with _get_async_client() as client:
            response = await client.post("/resolve", json=payload)
            data = _handle_response(response)
    except httpx.RequestError as e:
        logger.error("Rust pricing service unavailable: %s", e)
        raise RustPricingUnavailable(str(e)) from e

    return ComponentPricingResult(
        charge_amount=Decimal(data["charge_amount"]),
        charge_currency=data["charge_currency"],
        cost_amount=Decimal(data["cost_amount"]) if data.get("cost_amount") else None,
        cost_currency=data["cost_currency"],
        price_rule_id=UUID(data["price_rule_id"]),
        has_cost=data["has_cost"],
    )
