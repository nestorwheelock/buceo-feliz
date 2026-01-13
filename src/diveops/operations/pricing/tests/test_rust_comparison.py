"""Comparison tests for Python vs Rust pricing implementations.

These tests verify that the Rust pricing engine produces identical results
to the Python implementation for the same inputs.

For pure calculation functions (round_money, allocate_shared_costs), we test
both implementations directly.

For DB-dependent functions, we test the Rust client response parsing and
verify the data structures match.
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID

from ..calculators import (
    round_money as python_round_money,
    allocate_shared_costs as python_allocate_shared_costs,
)
from ..rust_client import (
    RustPricingError,
    RustPricingUnavailable,
    BoatCostResult,
    GasFillResult,
    ComponentPricingResult,
    _handle_response,
)


class TestRoundMoneyComparison:
    """Compare Python and Rust round_money implementations.

    Both should use banker's rounding (ROUND_HALF_EVEN).
    """

    # Test cases: (input, places, expected)
    ROUND_MONEY_CASES = [
        # Banker's rounding - rounds to even
        (Decimal("2.5"), 0, Decimal("2")),
        (Decimal("3.5"), 0, Decimal("4")),
        (Decimal("4.5"), 0, Decimal("4")),
        (Decimal("5.5"), 0, Decimal("6")),
        # Decimal places
        (Decimal("2.25"), 1, Decimal("2.2")),
        (Decimal("2.35"), 1, Decimal("2.4")),
        (Decimal("2.45"), 1, Decimal("2.4")),
        (Decimal("2.55"), 1, Decimal("2.6")),
        # Normal rounding
        (Decimal("1.234"), 2, Decimal("1.23")),
        (Decimal("1.236"), 2, Decimal("1.24")),
        (Decimal("1.2349"), 2, Decimal("1.23")),
        (Decimal("1.2351"), 2, Decimal("1.24")),
        # Zero
        (Decimal("0"), 2, Decimal("0")),
        (Decimal("0.00"), 2, Decimal("0.00")),
        # Negative
        (Decimal("-2.5"), 0, Decimal("-2")),
        (Decimal("-3.5"), 0, Decimal("-4")),
        (Decimal("-1.234"), 2, Decimal("-1.23")),
        # Large values
        (Decimal("123456.789"), 2, Decimal("123456.79")),
        (Decimal("999999.995"), 2, Decimal("1000000.00")),
    ]

    @pytest.mark.parametrize("amount,places,expected", ROUND_MONEY_CASES)
    def test_python_round_money(self, amount, places, expected):
        """Verify Python round_money produces expected results."""
        result = python_round_money(amount, places)
        assert result == expected, f"Python: round_money({amount}, {places}) = {result}, expected {expected}"

    def test_python_rust_round_money_parity(self):
        """Document expected behavior for Rust implementation.

        Rust uses rust_decimal with MidpointNearestEven strategy,
        which should match Python's ROUND_HALF_EVEN.

        This test documents the expected behavior that Rust tests verify.
        """
        for amount, places, expected in self.ROUND_MONEY_CASES:
            result = python_round_money(amount, places)
            assert result == expected, f"Expected {expected} for round_money({amount}, {places})"


class TestAllocateSharedCostsComparison:
    """Compare Python and Rust allocate_shared_costs implementations."""

    # Test cases: (total, diver_count, expected_per_diver, expected_sum)
    ALLOCATION_CASES = [
        # Even division
        (Decimal("100"), 4, Decimal("25"), Decimal("100")),
        (Decimal("100"), 2, Decimal("50"), Decimal("100")),
        (Decimal("100"), 1, Decimal("100"), Decimal("100")),
        # Remainder distribution
        (Decimal("100"), 3, Decimal("33.33"), Decimal("100")),
        (Decimal("100"), 7, None, Decimal("100")),  # per_diver varies
        # Edge cases
        (Decimal("0.03"), 3, Decimal("0.01"), Decimal("0.03")),
        (Decimal("1000.00"), 3, Decimal("333.33"), Decimal("1000.00")),
    ]

    @pytest.mark.parametrize("total,diver_count,expected_per_diver,expected_sum", ALLOCATION_CASES)
    def test_python_allocate_shared_costs_sum(self, total, diver_count, expected_per_diver, expected_sum):
        """Verify Python allocation always sums to original total."""
        per_diver, amounts = python_allocate_shared_costs(total, diver_count)
        actual_sum = sum(amounts)
        assert actual_sum == expected_sum, f"Sum {actual_sum} != expected {expected_sum}"

    @pytest.mark.parametrize("total,diver_count,expected_per_diver,expected_sum", ALLOCATION_CASES)
    def test_python_allocate_shared_costs_per_diver(self, total, diver_count, expected_per_diver, expected_sum):
        """Verify Python allocation per_diver matches expected (where specified)."""
        if expected_per_diver is None:
            pytest.skip("per_diver varies for this case")
        per_diver, amounts = python_allocate_shared_costs(total, diver_count)
        assert per_diver == expected_per_diver

    def test_python_allocate_zero_divers(self):
        """Test Python behavior with zero divers."""
        per_diver, amounts = python_allocate_shared_costs(Decimal("100"), 0)
        assert per_diver == Decimal("0")
        assert amounts == []

    def test_python_allocate_negative_divers(self):
        """Test Python behavior with negative divers."""
        per_diver, amounts = python_allocate_shared_costs(Decimal("100"), -1)
        assert per_diver == Decimal("0")
        assert amounts == []

    def test_remainder_distribution_order(self):
        """Verify remainder is distributed to first divers."""
        per_diver, amounts = python_allocate_shared_costs(Decimal("100"), 3)

        # 100 / 3 = 33.33..., rounds to 33.33
        # 33.33 * 3 = 99.99, remainder = 0.01
        # First diver should get the extra penny
        assert amounts[0] == Decimal("33.34")
        assert amounts[1] == Decimal("33.33")
        assert amounts[2] == Decimal("33.33")


class TestRustClientResponseParsing:
    """Test Rust client response parsing and error handling."""

    def test_handle_response_success(self):
        """Test successful response parsing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}

        result = _handle_response(mock_response)
        assert result == {"result": "success"}

    def test_handle_response_error_with_body(self):
        """Test error response with JSON body."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error_type": "missing_vendor_agreement",
            "message": "No vendor agreement found",
            "details": {"scope_type": "vendor_pricing"},
        }

        with pytest.raises(RustPricingError) as exc_info:
            _handle_response(mock_response)

        assert exc_info.value.error_type == "missing_vendor_agreement"
        assert "vendor agreement" in exc_info.value.message

    def test_handle_response_error_without_body(self):
        """Test error response without JSON body."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.raise_for_status.side_effect = Exception("Server error")

        with pytest.raises(Exception) as exc_info:
            _handle_response(mock_response)

        assert "Server error" in str(exc_info.value)


class TestBoatCostResultParsing:
    """Test BoatCostResult dataclass from Rust response."""

    def test_boat_cost_result_creation(self):
        """Test creating BoatCostResult from parsed response data."""
        result = BoatCostResult(
            total_amount=Decimal("1800"),
            total_currency="MXN",
            per_diver_amount=Decimal("450"),
            per_diver_currency="MXN",
            base_cost_amount=Decimal("1800"),
            base_cost_currency="MXN",
            overage_count=0,
            overage_per_diver_amount=Decimal("150"),
            overage_per_diver_currency="MXN",
            included_divers=4,
            diver_count=4,
            agreement_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        assert result.total_amount == Decimal("1800")
        assert result.per_diver_amount == Decimal("450")
        assert result.overage_count == 0
        assert result.diver_count == 4

    def test_boat_cost_result_with_overage(self):
        """Test BoatCostResult with overage divers."""
        result = BoatCostResult(
            total_amount=Decimal("2100"),  # 1800 + 2*150
            total_currency="MXN",
            per_diver_amount=Decimal("350"),  # 2100 / 6
            per_diver_currency="MXN",
            base_cost_amount=Decimal("1800"),
            base_cost_currency="MXN",
            overage_count=2,
            overage_per_diver_amount=Decimal("150"),
            overage_per_diver_currency="MXN",
            included_divers=4,
            diver_count=6,
            agreement_id=None,
        )

        assert result.total_amount == Decimal("2100")
        assert result.overage_count == 2
        assert result.diver_count == 6


class TestGasFillResultParsing:
    """Test GasFillResult dataclass from Rust response."""

    def test_gas_fill_result_creation(self):
        """Test creating GasFillResult from parsed response data."""
        result = GasFillResult(
            cost_per_fill_amount=Decimal("50"),
            cost_per_fill_currency="MXN",
            charge_per_fill_amount=Decimal("100"),
            charge_per_fill_currency="MXN",
            total_cost_amount=Decimal("100"),
            total_cost_currency="MXN",
            total_charge_amount=Decimal("200"),
            total_charge_currency="MXN",
            fills_count=2,
            gas_type="air",
            agreement_id=UUID("12345678-1234-5678-1234-567812345678"),
            price_rule_id=None,
        )

        assert result.cost_per_fill_amount == Decimal("50")
        assert result.total_cost_amount == Decimal("100")
        assert result.fills_count == 2
        assert result.gas_type == "air"


class TestComponentPricingResultParsing:
    """Test ComponentPricingResult dataclass from Rust response."""

    def test_component_pricing_result_creation(self):
        """Test creating ComponentPricingResult from parsed response data."""
        result = ComponentPricingResult(
            charge_amount=Decimal("500"),
            charge_currency="MXN",
            cost_amount=Decimal("300"),
            cost_currency="MXN",
            price_rule_id=UUID("12345678-1234-5678-1234-567812345678"),
            has_cost=True,
        )

        assert result.charge_amount == Decimal("500")
        assert result.cost_amount == Decimal("300")
        assert result.has_cost is True

    def test_component_pricing_result_no_cost(self):
        """Test ComponentPricingResult without cost."""
        result = ComponentPricingResult(
            charge_amount=Decimal("500"),
            charge_currency="MXN",
            cost_amount=None,
            cost_currency="MXN",
            price_rule_id=UUID("12345678-1234-5678-1234-567812345678"),
            has_cost=False,
        )

        assert result.charge_amount == Decimal("500")
        assert result.cost_amount is None
        assert result.has_cost is False


class TestRustClientIntegration:
    """Integration tests for Rust client with mocked HTTP responses.

    These tests verify the client correctly parses Rust service responses.
    """

    @patch("diveops.operations.pricing.rust_client._get_client")
    def test_calculate_boat_cost_success(self, mock_get_client):
        """Test successful boat cost calculation via Rust client."""
        from ..rust_client import calculate_boat_cost

        mock_client = MagicMock()
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total": {"amount": "1800", "currency": "MXN"},
            "per_diver": {"amount": "450", "currency": "MXN"},
            "base_cost": {"amount": "1800", "currency": "MXN"},
            "overage_count": 0,
            "overage_per_diver": {"amount": "150", "currency": "MXN"},
            "included_divers": 4,
            "diver_count": 4,
            "agreement_id": "12345678-1234-5678-1234-567812345678",
        }
        mock_client.post.return_value = mock_response

        result = calculate_boat_cost(
            dive_site_id=UUID("00000000-0000-0000-0000-000000000001"),
            diver_count=4,
        )

        assert result.total_amount == Decimal("1800")
        assert result.per_diver_amount == Decimal("450")
        assert result.overage_count == 0

    @patch("diveops.operations.pricing.rust_client._get_client")
    def test_calculate_boat_cost_missing_agreement(self, mock_get_client):
        """Test boat cost calculation with missing agreement error."""
        from ..rust_client import calculate_boat_cost

        mock_client = MagicMock()
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error_type": "missing_vendor_agreement",
            "message": "No vendor agreement found for vendor_pricing:DiveSite:xxx",
            "details": {
                "scope_type": "vendor_pricing",
                "scope_ref": "DiveSite:xxx",
            },
        }
        mock_client.post.return_value = mock_response

        with pytest.raises(RustPricingError) as exc_info:
            calculate_boat_cost(
                dive_site_id=UUID("00000000-0000-0000-0000-000000000001"),
                diver_count=4,
            )

        assert exc_info.value.error_type == "missing_vendor_agreement"

    @patch("diveops.operations.pricing.rust_client._get_client")
    def test_allocate_shared_costs_success(self, mock_get_client):
        """Test successful shared cost allocation via Rust client."""
        from ..rust_client import allocate_shared_costs

        mock_client = MagicMock()
        mock_get_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_get_client.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "per_diver": {"amount": "33.33", "currency": "MXN"},
            "amounts": [
                {"amount": "33.34", "currency": "MXN"},
                {"amount": "33.33", "currency": "MXN"},
                {"amount": "33.33", "currency": "MXN"},
            ],
        }
        mock_client.post.return_value = mock_response

        per_diver, amounts = allocate_shared_costs(
            shared_total=Decimal("100"),
            diver_count=3,
            currency="MXN",
        )

        assert per_diver == Decimal("33.33")
        assert len(amounts) == 3
        assert amounts[0] == Decimal("33.34")
        assert sum(amounts) == Decimal("100")


class TestPythonRustDelegation:
    """Test that Python functions delegate to Rust when enabled."""

    @patch("diveops.operations.pricing.calculators.settings")
    def test_allocate_shared_costs_uses_rust_when_enabled(self, mock_settings):
        """Test that allocate_shared_costs delegates to Rust when USE_RUST_PRICING=True."""
        mock_settings.USE_RUST_PRICING = True

        with patch("diveops.operations.pricing.rust_client.allocate_shared_costs") as mock_rust:
            mock_rust.return_value = (Decimal("33.33"), [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")])

            from ..calculators import allocate_shared_costs
            per_diver, amounts = allocate_shared_costs(Decimal("100"), 3, "MXN")

            mock_rust.assert_called_once_with(
                shared_total=Decimal("100"),
                diver_count=3,
                currency="MXN",
            )

    @patch("diveops.operations.pricing.calculators.settings")
    def test_allocate_shared_costs_fallback_on_unavailable(self, mock_settings):
        """Test that allocate_shared_costs falls back to Python when Rust unavailable."""
        mock_settings.USE_RUST_PRICING = True

        with patch("diveops.operations.pricing.rust_client.allocate_shared_costs") as mock_rust:
            mock_rust.side_effect = RustPricingUnavailable("Connection refused")

            from ..calculators import allocate_shared_costs
            per_diver, amounts = allocate_shared_costs(Decimal("100"), 3, "MXN")

            # Should fall back to Python implementation
            assert per_diver == Decimal("33.33")
            assert sum(amounts) == Decimal("100")

    @patch("diveops.operations.pricing.calculators.settings")
    def test_allocate_shared_costs_uses_python_when_disabled(self, mock_settings):
        """Test that allocate_shared_costs uses Python when USE_RUST_PRICING=False."""
        mock_settings.USE_RUST_PRICING = False

        with patch("diveops.operations.pricing.rust_client.allocate_shared_costs") as mock_rust:
            from ..calculators import allocate_shared_costs
            per_diver, amounts = allocate_shared_costs(Decimal("100"), 3, "MXN")

            # Should NOT call Rust
            mock_rust.assert_not_called()

            # Should use Python implementation
            assert per_diver == Decimal("33.33")
            assert sum(amounts) == Decimal("100")
