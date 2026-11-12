import math
from datetime import date

from src.classification import calculate_cv, add_abc_class

from src.forecasting import (
    calculate_safety_stock,
    calculate_reorder_point,
    calculate_order_quantity,
    calculate_eoq,
)

from src.simulation import (
    receive_orders,
    apply_shelf_life_rule,
    apply_budget,
    expire_stock,
    process_recommendations,
    process_demand,
    place_funded_orders,
    get_inventory_position,
    run_simulation,
    simulate_day,
    create_daily_stock_rows,
)


def test_cv():
    values = [6, 7, 9, 6, 6, 5, 5, 7]

    mean = sum(values) / len(values)

    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / len(values)

    expected_cv = math.sqrt(variance) / mean

    actual_cv = calculate_cv(values)

    assert round(actual_cv, 4) == round(expected_cv, 4)


def test_reorder_point():
    daily_demand = 0.1986
    lead_time = 8
    safety_stock = 2

    expected = math.ceil(
        daily_demand * lead_time + safety_stock
    )

    actual = calculate_reorder_point(
        daily_demand,
        lead_time,
        safety_stock
    )

    assert actual == expected
    assert actual == 4


def test_order_quantity_for_c_class():
    forecast_units = 6.27
    eoq = 29.11
    moq = 24
    pack_size = 12

    actual = calculate_order_quantity(
        "C",
        forecast_units,
        eoq,
        moq,
        pack_size
    )

    assert actual == 24


def test_eoq():
    forecast_units = 6.27
    unit_cost = 37
    ordering_cost = 500
    holding_cost_percent = 20

    holding_cost = (
        unit_cost * holding_cost_percent / 100
    )

    expected = math.sqrt(
        (2 * forecast_units * ordering_cost)
        / holding_cost
    )

    actual = calculate_eoq(
        forecast_units,
        unit_cost,
        ordering_cost,
        holding_cost_percent
    )

    assert round(actual, 2) == round(expected, 2)


def test_shelf_life_rejection():
    recommendation = {
        "order_qty": 24
    }

    sku_info = {
        "shelf_life_days": 20,
        "moq": 24,
        "pack_size": 12
    }

    forecast = {
        "daily_demand": 0.1986
    }

    result = apply_shelf_life_rule(
        recommendation,
        sku_info,
        forecast,
        0.80
    )

    assert result["shelf_cap"] == 3
    assert result["decision"] == "REJECTED"
    assert result["reason"] == "SHELF_LIFE"


def test_sku018_reorder_point_example():
    daily_demand = 0.1986
    lead_time_days = 8
    safety_stock = 2

    expected_rop = 4

    actual_rop = calculate_reorder_point(
        daily_demand,
        lead_time_days,
        safety_stock
    )

    assert actual_rop == expected_rop

def test_abc_classification_boundary():
    results = [
        {
            "sku_id": "SKU-A",
            "annual_value": 70
        },
        {
            "sku_id": "SKU-B",
            "annual_value": 20
        },
        {
            "sku_id": "SKU-C",
            "annual_value": 10
        }
    ]

    result = add_abc_class(results)

    assert result[0]["abc"] == "A"
    assert result[1]["abc"] == "B"
    assert result[2]["abc"] == "C"
    assert result[0]["cum_share_pct"] == 70.0


def test_safety_stock():
    daily_demand = 0.1986
    lead_time_days = 8
    lead_time_var_days2 = 5
    z_value = 1.28

    result = calculate_safety_stock(
        demand_history=[
            {"sku_id": "SKU-018", "month": "2024-10", "units": "6"},
            {"sku_id": "SKU-018", "month": "2024-11", "units": "7"},
            {"sku_id": "SKU-018", "month": "2024-12", "units": "9"},
            {"sku_id": "SKU-018", "month": "2025-01", "units": "6"},
            {"sku_id": "SKU-018", "month": "2025-02", "units": "6"},
            {"sku_id": "SKU-018", "month": "2025-03", "units": "5"},
            {"sku_id": "SKU-018", "month": "2025-04", "units": "5"},
            {"sku_id": "SKU-018", "month": "2025-05", "units": "7"},
            {"sku_id": "SKU-018", "month": "2025-06", "units": "5"},
            {"sku_id": "SKU-018", "month": "2025-07", "units": "7"},
            {"sku_id": "SKU-018", "month": "2025-08", "units": "4"},
            {"sku_id": "SKU-018", "month": "2025-09", "units": "7"},
            {"sku_id": "SKU-018", "month": "2025-10", "units": "7"},
            {"sku_id": "SKU-018", "month": "2025-11", "units": "6"},
            {"sku_id": "SKU-018", "month": "2025-12", "units": "7"},
            {"sku_id": "SKU-018", "month": "2026-01", "units": "7"},
            {"sku_id": "SKU-018", "month": "2026-02", "units": "7"},
            {"sku_id": "SKU-018", "month": "2026-03", "units": "3"},
            {"sku_id": "SKU-018", "month": "2026-04", "units": "7"},
            {"sku_id": "SKU-018", "month": "2026-05", "units": "6"},
            {"sku_id": "SKU-018", "month": "2026-06", "units": "3"},
            {"sku_id": "SKU-018", "month": "2026-07", "units": "4"},
            {"sku_id": "SKU-018", "month": "2026-08", "units": "6"},
            {"sku_id": "SKU-018", "month": "2026-09", "units": "6"},
        ],
        sku_id="SKU-018",
        daily_demand=daily_demand,
        lead_time_days=lead_time_days,
        lead_time_var_days2=lead_time_var_days2,
        z_value=z_value,
        xyz="X"
    )

    assert result == 2


def test_moq_and_pack_size_rounding():
    forecast_units = 6.27
    eoq = 29.11
    moq = 24
    pack_size = 12

    actual = calculate_order_quantity(
        "C",
        forecast_units,
        eoq,
        moq,
        pack_size
    )

    assert actual == 24


def test_fifo_backorder_receipt():
    current_date = date(2026, 10, 8)

    stock = []

    open_orders = [
        {
            "po_id": "PO-0011",
            "sku_id": "SKU-027",
            "quantity": "21",
            "order_date": "2026-09-17",
            "expected_receipt_date": "2026-10-08"
        }
    ]

    backorders = {
        "SKU-027": 43
    }

    received, filled = receive_orders(
        current_date,
        stock,
        open_orders,
        backorders
    )

    assert received["SKU-027"] == 21
    assert filled["SKU-027"] == 21
    assert backorders["SKU-027"] == 22
    assert len(stock) == 0
    assert len(open_orders) == 0


def test_budget_funding():
    recommendations = [
        {
            "sku_id": "SKU-001",
            "class_code": "AX",
            "days_of_cover": 2,
            "order_qty": 10,
            "unit_cost": 100
        },
        {
            "sku_id": "SKU-002",
            "class_code": "BX",
            "days_of_cover": 3,
            "order_qty": 10,
            "unit_cost": 100
        },
        {
            "sku_id": "SKU-003",
            "class_code": "CX",
            "days_of_cover": 4,
            "order_qty": 10,
            "unit_cost": 100
        }
    ]

    remaining_budget = apply_budget(
        recommendations,
        monthly_budget=1500,
        budget_used=0
    )

    assert recommendations[0]["decision"] == "FUNDED"
    assert recommendations[1]["decision"] == "DEFERRED"
    assert recommendations[2]["decision"] == "DEFERRED"

    assert recommendations[0]["order_value"] == 1000
    assert recommendations[1]["order_value"] == 1000
    assert recommendations[2]["order_value"] == 1000

    assert remaining_budget == 500

def test_stock_expiry():
    stock = [
        {
            "batch_id": "BAT-0062",
            "sku_id": "SKU-053",
            "quantity": 10,
            "received_date": "2026-02-11"
        }
    ]

    sku_lookup = {
        "SKU-053": {
            "shelf_life_days": 240
        }
    }

    expired = expire_stock(
        date(2026, 10, 10),
        stock,
        sku_lookup
    )

    assert expired["SKU-053"] == 10
    assert len(stock) == 0


def test_supplier_consolidation():
    recommendations = [
        {
            "sku_id": "SKU-001",
            "order_qty": 50,
            "inventory_position": 40,
            "unit_cost": 100,
            "class_code": "AX",
            "days_of_cover": 5,
            "decision": "PENDING",
            "consolidated": False
        },
        {
            "sku_id": "SKU-002",
            "order_qty": 60,
            "inventory_position": 40,
            "unit_cost": 100,
            "class_code": "AX",
            "days_of_cover": 5,
            "decision": "PENDING",
            "consolidated": False
        }
    ]

    sku_lookup = {
        "SKU-001": {
            "supplier_id": "SUP-01",
            "pack_size": 10,
            "moq": 10,
            "shelf_life_days": 100,
            "unit_cost": 100
        },
        "SKU-002": {
            "supplier_id": "SUP-01",
            "pack_size": 10,
            "moq": 10,
            "shelf_life_days": 100,
            "unit_cost": 100
        }
    }

    forecast_lookup = {
        "SKU-001": {
            "reorder_point": 100,
            "eoq": 20,
            "daily_demand": 2

        },
        "SKU-002": {
            "reorder_point": 100,
            "eoq": 20,
            "daily_demand": 2
        }
    }

    processed, remaining = process_recommendations(
        recommendations,
        sku_lookup,
        forecast_lookup,
        monthly_budget=100000,
        budget_used=0,
        shelf_life_usage=0.80
    )

    sku_001 = next(
        row for row in processed
        if row["sku_id"] == "SKU-001"
    )

    sku_002 = next(
        row for row in processed
        if row["sku_id"] == "SKU-002"
    )

    assert sku_001["consolidated"] is True
    assert sku_002["consolidated"] is False
    assert sku_001["order_qty"] == 80
    assert sku_002["order_qty"] == 60

def test_ab_backorder_and_c_lost_sales():
    daily_demand = [
        {
            "date": "2026-10-01",
            "sku_id": "SKU-A",
            "units": "5"
        },
        {
            "date": "2026-10-01",
            "sku_id": "SKU-C",
            "units": "5"
        }
    ]

    stock = []
    backorders = {}

    sku_lookup = {
        "SKU-A": {
            "abc": "A"
        },
        "SKU-C": {
            "abc": "C"
        }
    }

    demand, shipped, backordered, lost = process_demand(
        date(2026, 10, 1),
        daily_demand,
        stock,
        backorders,
        sku_lookup
    )

    assert shipped.get("SKU-A", 0) == 0
    assert backordered.get("SKU-A", 0) == 5
    assert lost.get("SKU-A", 0) == 0

    assert shipped.get("SKU-C", 0) == 0
    assert backordered.get("SKU-C", 0) == 0
    assert lost.get("SKU-C", 0) == 5

def test_duplicate_daily_demand_is_ignored():
    daily_demand = [
        {
            "date": "2026-11-17",
            "sku_id": "SKU-001",
            "units": "5"
        },
        {
            "date": "2026-11-17",
            "sku_id": "SKU-001",
            "units": "7"
        }
    ]

    stock = [
        {
            "batch_id": "BAT-0001",
            "sku_id": "SKU-001",
            "quantity": 10,
            "received_date": "2026-09-01"
        }
    ]

    backorders = {}

    sku_lookup = {
        "SKU-001": {
            "abc": "A"
        }
    }

    demand, shipped, backordered, lost = process_demand(
        date(2026, 11, 17),
        daily_demand,
        stock,
        backorders,
        sku_lookup
    )

    assert demand["SKU-001"] == 5

def test_funded_order_uses_lead_time():
    recommendations = [
        {
            "date": "2026-10-01",
            "sku_id": "SKU-001",
            "order_qty": 10,
            "decision": "FUNDED"
        }
    ]

    sku_lookup = {
        "SKU-001": {
            "lead_time_days": 8
        }
    }

    open_orders = []

    place_funded_orders(
        date(2026, 10, 1),
        recommendations,
        open_orders,
        sku_lookup
    )

    assert len(open_orders) == 1
    assert open_orders[0]["expected_receipt_date"] == date(2026, 10, 9)

def test_inventory_position():
    stock = [
        {
            "sku_id": "SKU-001",
            "quantity": 30
        }
    ]

    open_orders = [
        {
            "sku_id": "SKU-001",
            "quantity": 20
        }
    ]

    backorders = {
        "SKU-001": 5
    }

    result = get_inventory_position(
        stock,
        open_orders,
        backorders,
        "SKU-001"
    )

    assert result == 45

def test_monthly_budget_resets():
    daily_demand = []

    stock = []

    open_orders = []

    backorders = {}

    sku_lookup = {}

    forecast_lookup = {}

    daily_rows, recommendations = run_simulation(
        start_date=date(2026, 11, 1),
        days=1,
        daily_demand=daily_demand,
        stock=stock,
        open_orders=open_orders,
        backorders=backorders,
        sku_lookup=sku_lookup,
        forecast_lookup=forecast_lookup,
        monthly_budget=5000000,
        shelf_life_usage=0.80
    )

    assert daily_rows == []
    assert recommendations == []

def test_simulate_day_sequence():
    stock = [
        {
            "batch_id": "BAT-001",
            "sku_id": "SKU-001",
            "quantity": 5,
            "received_date": "2026-09-01"
        }
    ]

    open_orders = [
        {
            "po_id": "PO-001",
            "sku_id": "SKU-001",
            "quantity": 10,
            "order_date": "2026-09-30",
            "expected_receipt_date": "2026-10-01"
        }
    ]

    backorders = {}

    daily_demand = [
        {
            "date": "2026-10-01",
            "sku_id": "SKU-001",
            "units": "8"
        }
    ]

    sku_lookup = {
        "SKU-001": {
            "abc": "A",
            "shelf_life_days": 100
        }
    }

    result = simulate_day(
        date(2026, 10, 1),
        daily_demand,
        stock,
        open_orders,
        backorders,
        sku_lookup
    )

    assert "expired" in result
    assert "received" in result
    assert "backorder_filled" in result
    assert "demand" in result
    assert "shipped" in result
    assert "backordered" in result
    assert "lost" in result
    assert "backorder_balance" in result

    assert result["demand"]["SKU-001"] == 8

def test_daily_stock_row():
    sku_lookup = {
        "SKU-001": {
            "unit_cost": 100
        }
    }

    opening_stock = {
        "SKU-001": 10
    }

    stock = [
        {
            "batch_id": "BAT-001",
            "sku_id": "SKU-001",
            "quantity": 7,
            "received_date": "2026-09-01"
        }
    ]

    open_orders = [
        {
            "po_id": "PO-001",
            "sku_id": "SKU-001",
            "quantity": 10,
            "expected_receipt_date": "2026-10-05"
        }
    ]

    result = {
        "expired": {"SKU-001": 0},
        "received": {"SKU-001": 5},
        "backorder_filled": {"SKU-001": 0},
        "demand": {"SKU-001": 8},
        "shipped": {"SKU-001": 8},
        "backordered": {"SKU-001": 0},
        "lost": {"SKU-001": 0},
        "backorder_balance": {"SKU-001": 0}
    }

    rows = create_daily_stock_rows(
        date(2026, 10, 1),
        sku_lookup,
        opening_stock,
        stock,
        open_orders,
        result
    )

    assert len(rows) == 1

    row = rows[0]

    assert row["date"] == date(2026,10,1)
    assert row["sku_id"] == "SKU-001"
    assert row["opening_on_hand"] == 10
    assert row["expired"] == 0
    assert row["received"] == 5
    assert row["backorder_filled"] == 0
    assert row["demand"] == 8
    assert row["shipped"] == 8
    assert row["backordered"] == 0
    assert row["lost"] == 0
    assert row["closing_on_hand"] == 7
    assert row["on_order"] == 10
    assert row["backorder_balance"] == 0

def test_full_simulation_runs():
    daily_demand = [
        {
            "date": "2026-10-01",
            "sku_id": "SKU-001",
            "units": "8"
        }
    ]

    stock = [
        {
            "batch_id": "BAT-001",
            "sku_id": "SKU-001",
            "quantity": 10,
            "received_date": "2026-09-01"
        }
    ]

    open_orders = []

    backorders = {}

    sku_lookup = {
        "SKU-001": {
            "abc": "A",
            "class_code": "AX",
            "supplier_id": "SUP-01",
            "unit_cost": 100,
            "lead_time_days": 5,
            "shelf_life_days": 100,
            "pack_size": 1,
            "moq": 1
        }
    }
    
    forecast_lookup = {
        "SKU-001": {
            "reorder_point": 20,
            "eoq": 10,
            "order_qty": 10,
            "daily_demand": 8
        }
    }

    daily_rows, recommendations = run_simulation(
        start_date=date(2026, 10, 1),
        days=1,
        daily_demand=daily_demand,
        stock=stock,
        open_orders=open_orders,
        backorders=backorders,
        sku_lookup=sku_lookup,
        forecast_lookup=forecast_lookup,
        monthly_budget=5000000,
        shelf_life_usage=0.80
    )

    assert len(daily_rows) == 1
    assert isinstance(recommendations, list)