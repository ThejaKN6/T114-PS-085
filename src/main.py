import math

from src.loader import load_csv

from src.classification import (
    build_classification
)

from src.forecasting import (
    calculate_seasonal_indices,
    calculate_forecast_units,
    calculate_safety_stock,
    calculate_reorder_point,
    calculate_order_quantity,
    calculate_eoq
)

from src.simulation import (
    run_simulation,
    simulate_day,
    add_reorder_to_day,
    create_daily_stock_rows,
    process_recommendations,
    place_funded_orders,
    save_opening_stock,
    to_date
)

from src.reports import (
    write_classification_report,
    write_seasonal_indices_report,
    write_forecast_report,
    write_recommendations_report,
    write_daily_stock_report,
    write_kpi_report
)

def make_lookup(rows, key):
    return {
        row[key]: row
        for row in rows
    }

def get_parameter(parameters, name):
    for row in parameters:
        if row["parameter"] == name:
            return row["value"]
    return None

def load_data():
    suppliers = load_csv(
        "data/suppliers.csv"
    )

    parameters = load_csv(
        "data/parameters.csv"
    )

    service_levels = load_csv(
        "data/service_levels.csv"
    )

    skus = load_csv(
        "data/skus.csv"
    )

    demand_history = load_csv(
        "data/demand_history.csv"
    )

    opening_stock = load_csv(
        "data/opening_stock.csv"
    )

    open_orders = load_csv(
        "data/open_orders.csv"
    )

    daily_demand = load_csv(
        "data/daily_demand.csv"
    )

    print(
        "Daily demand rows:",
        len(daily_demand)
    )

    with open(
        "data/commands.txt",
        encoding="utf-8"
    ) as file:
        commands = [
            line.strip()
            for line in file
            if line.strip()
            and not line.strip().startswith("#")
        ]

    return (
        suppliers,
        parameters,
        service_levels,
        skus,
        demand_history,
        opening_stock,
        open_orders,
        daily_demand,
        commands
    )

def build_forecast_plan(
    demand_history,
    skus,
    sku_lookup,
    seasonal_indices,
    forecast_month
):
    ordering_cost = 500
    holding_cost_percent = 20
    results = []

    for sku in skus:
        sku_id = sku["sku_id"]

        forecast_units = calculate_forecast_units(
            demand_history,
            seasonal_indices,
            sku_id,
            forecast_month
        )

        daily_demand = (
            forecast_units / 30
        )

        lead_time_days = int(
            sku["lead_time_days"]
        )

        lead_time_var_days2 = float(
            sku["lead_time_var_days2"]
        )

        z_value = float(
            sku_lookup[sku_id]["z_value"]
        )

        xyz = sku_lookup[
            sku_id
        ]["xyz"]

        safety_stock = calculate_safety_stock(
            demand_history,
            sku_id,
            daily_demand,
            lead_time_days,
            lead_time_var_days2,
            z_value,
            xyz
        )

        reorder_point = calculate_reorder_point(
            daily_demand,
            lead_time_days,
            safety_stock
        )

        eoq = calculate_eoq(
            forecast_units,
            float(sku["unit_cost"]),
            ordering_cost,
            holding_cost_percent
        )

        order_qty = calculate_order_quantity(
            sku_lookup[sku_id]["abc"],
            forecast_units,
            eoq,
            int(sku["moq"]),
            int(sku["pack_size"])
        )

        shelf_life_days = int(
            sku["shelf_life_days"]
        )

        if shelf_life_days > 0:
            shelf_cap = math.floor(
                daily_demand
                * 0.8
                * shelf_life_days
            )
        else:
            shelf_cap = 0

        results.append({
            "sku_id": sku_id,
            "month": forecast_month,
            "forecast_units": forecast_units,
            "daily_demand": daily_demand,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "eoq": eoq,
            "order_qty": order_qty,
            "shelf_cap": shelf_cap
        })

    return results

def build_kpi_report(
    daily_rows,
    skus
):
    sku_lookup = make_lookup(
        skus,
        "sku_id"
    )

    kpi = {}

    for sku in skus:
        sku_id = sku["sku_id"]

        kpi[sku_id] = {
            "sku_id": sku_id,
            "units_demanded": 0,
            "units_shipped_same_day": 0,
            "stockout_days": 0,
            "expired_units": 0,
            "expired_value": 0.0,
            "inventory_value_total": 0.0,
            "days": 0
        }

    for row in daily_rows:
        sku_id = row["sku_id"]

        if sku_id not in kpi:
            continue

        data = kpi[sku_id]

        demand = int(row["demand"])
        shipped = int(row["shipped"])
        closing_stock = int(row["closing_on_hand"])
        expired = int(row["expired"])

        unit_cost = float(
            sku_lookup[sku_id]["unit_cost"]
        )

        data["units_demanded"] += demand
        data["units_shipped_same_day"] += shipped

        if demand > shipped:
            data["stockout_days"] += 1

        data["expired_units"] += expired

        data["expired_value"] += (
            expired * unit_cost
        )

        data["inventory_value_total"] += (
            closing_stock * unit_cost
        )

        data["days"] += 1

    results = []

    total_demand = 0
    total_shipped = 0
    total_stockout_days = 0
    total_expired_units = 0
    total_expired_value = 0.0
    total_inventory_value = 0.0
    total_days = 0

    for sku in skus:
        sku_id = sku["sku_id"]
        data = kpi[sku_id]

        if data["units_demanded"] > 0:
            fill_rate = (
                data["units_shipped_same_day"]
                / data["units_demanded"]
                * 100
            )
        else:
            fill_rate = 100.0

        if data["days"] > 0:
            avg_inventory_value = (
                data["inventory_value_total"]
                / data["days"]
            )
        else:
            avg_inventory_value = 0.0

        results.append({
            "sku_id": sku_id,
            "units_demanded": data["units_demanded"],
            "units_shipped_same_day":
                data["units_shipped_same_day"],
            "fill_rate_pct": fill_rate,
            "stockout_days": data["stockout_days"],
            "expired_units": data["expired_units"],
            "expired_value": data["expired_value"],
            "avg_inventory_value":
                avg_inventory_value
        })

        total_demand += data["units_demanded"]
        total_shipped += data["units_shipped_same_day"]
        total_stockout_days += data["stockout_days"]
        total_expired_units += data["expired_units"]
        total_expired_value += data["expired_value"]
        total_inventory_value += data["inventory_value_total"]
        total_days += data["days"]

    if total_demand > 0:
        total_fill_rate = (
            total_shipped
            / total_demand
            * 100
        )
    else:
        total_fill_rate = 100.0

    if total_days > 0:
        total_avg_inventory = (
            total_inventory_value
            / total_days
        )
    else:
        total_avg_inventory = 0.0

    results.append({
        "sku_id": "TOTAL",
        "units_demanded": total_demand,
        "units_shipped_same_day": total_shipped,
        "fill_rate_pct": total_fill_rate,
        "stockout_days": total_stockout_days,
        "expired_units": total_expired_units,
        "expired_value": total_expired_value,
        "avg_inventory_value": total_avg_inventory
    })

    return results

def print_classification(rows):
    print()
    print("=" * 160)
    print("CLASSIFICATION")
    print("=" * 160)

    print(
        "SKU_ID | ANNUAL_UNITS | ANNUAL_VALUE | CUM_SHARE_PCT | "
        "ABC | CV | XYZ | ZERO_MONTHS | CLASS_CODE | "
        "SERVICE_LEVEL_PCT | Z_VALUE"
    )

    for row in rows:
        print(
            row["sku_id"], "|",
            f'{row["annual_units"]:.0f}', "|",
            f'{row["annual_value"]:.2f}', "|",
            f'{row["cum_share_pct"]:.2f}', "|",
            row["abc"], "|",
            f'{row["cv"]:.4f}', "|",
            row["xyz"], "|",
            row["zero_months"], "|",
            row["class_code"], "|",
            f'{row["service_level_pct"]:.2f}', "|",
            f'{row["z_value"]:.2f}'
        )

def print_seasonal_indices(rows):
    print()
    print("=" * 70)
    print("SEASONAL INDICES")
    print("=" * 70)

    print(
        "SKU_ID | MONTH_NO | SEASONAL_INDEX"
    )

    for row in rows:
        print(
            f'{row["sku_id"]} | '
            f'{row["month_no"]} | '
            f'{row["seasonal_index"]:.4f}'
        )

def print_forecast(rows):
    print()
    print("=" * 120)
    print("FORECAST PLAN")
    print("=" * 120)

    print(
        "SKU_ID | MONTH | FORECAST_UNITS | DAILY_DEMAND | "
        "SAFETY_STOCK | REORDER_POINT | EOQ | ORDER_QTY | SHELF_CAP"
    )

    for row in rows:
        print(
            row["sku_id"], "|",
            row["month"], "|",
            f'{row["forecast_units"]:.2f}', "|",
            f'{row["daily_demand"]:.2f}', "|",
            row["safety_stock"], "|",
            row["reorder_point"], "|",
            f'{row["eoq"]:.2f}', "|",
            row["order_qty"], "|",
            row["shelf_cap"]
        )

def print_recommendations(rows):
    print()
    print("=" * 120)
    print("RECOMMENDATIONS")
    print("=" * 120)

    print(
        "DATE | SKU_ID | CLASS_CODE | "
        "INVENTORY_POSITION | REORDER_POINT | "
        "DAYS_OF_COVER | ORDER_QTY | ORDER_VALUE | "
        "CONSOLIDATED | DECISION | REASON | "
        "BUDGET_REMAINING"
    )

    for row in rows:
        print(
            row["date"],
            "|",
            row["sku_id"],
            "|",
            row["class_code"],
            "|",
            row["inventory_position"],
            "|",
            row["reorder_point"],
            "|",
            f'{row["days_of_cover"]:.2f}',
            "|",
            row["order_qty"],
            "|",
            f'{row["order_value"]:.2f}',
            "|",
            row["consolidated"],
            "|",
            row["decision"],
            "|",
            row["reason"],
            "|",
            f'{row["budget_remaining_after"]:.2f}'
        )

def print_kpi(rows):
    print()
    print("=" * 110)
    print("KPI REPORT")
    print("=" * 110)

    print(
        "SKU_ID | UNITS_DEMANDED | UNITS_SHIPPED_SAME_DAY | "
        "FILL_RATE_PCT | STOCKOUT_DAYS | EXPIRED_UNITS | "
        "EXPIRED_VALUE | AVG_INVENTORY_VALUE"
    )

    print("-" * 110)

    for row in rows:
        print(
            row["sku_id"],
            "|",
            row["units_demanded"],
            "|",
            row["units_shipped_same_day"],
            "|",
            f'{row["fill_rate_pct"]:.2f}',
            "|",
            row["stockout_days"],
            "|",
            row["expired_units"],
            "|",
            f'{row["expired_value"]:.2f}',
            "|",
            f'{row["avg_inventory_value"]:.2f}'
        )

def process_commands(
    commands,
    sku_lookup,
    demand_history,
    skus,
    service_levels,
    daily_demand,
    stock,
    open_orders,
    backorders,
    forecast_lookup,
    seasonal_indices,
    monthly_budget,
    shelf_life_usage
):
    daily_rows = []
    recommendations = []
    forecast_plans = []
    budget_used = 0

    for command in commands:
        command = command.strip()

        if not command:
            continue

        if command.startswith("#"):
            continue

        parts = [
            part.strip()
            for part in command.split("|")
        ]

        command_name = parts[0]

        if command_name == "CLASSIFY":
            as_of_date = parts[1]

            classification = build_classification(
                demand_history,
                skus,
                service_levels,
                as_of_date
            )

            for row in classification:
                sku_lookup[row["sku_id"]].update(row)

            write_classification_report(
                classification
            )

        elif command_name == "SEASONAL_INDEX":
            seasonal_indices = calculate_seasonal_indices(
                demand_history
            )

            write_seasonal_indices_report(
                seasonal_indices
            )

        elif command_name == "FORECAST":
            forecast_month = parts[1]

            forecast_plan = build_forecast_plan(
                demand_history,
                skus,
                sku_lookup,
                seasonal_indices,
                forecast_month
            )

            forecast_lookup = {
                row["sku_id"]: row
                for row in forecast_plan
            }

            forecast_plans.extend(
                forecast_plan
            )

            print_forecast(
                forecast_plan
            )

        elif command_name == "RUN_DAY":
            current_date = to_date(
                parts[1]
            )

            if current_date.day == 1:
                budget_used = 0

            opening_stock = save_opening_stock(
                sku_lookup,
                stock
            )

            result = simulate_day(
                current_date,
                daily_demand,
                stock,
                open_orders,
                backorders,
                sku_lookup
            )

            day_recommendations = add_reorder_to_day(
                current_date,
                sku_lookup,
                stock,
                open_orders,
                backorders,
                forecast_lookup
            )

            (
                day_recommendations,
                budget_remaining
            ) = process_recommendations(
                day_recommendations,
                sku_lookup,
                forecast_lookup,
                monthly_budget,
                budget_used,
                shelf_life_usage
            )

            budget_used = (
                monthly_budget
                - budget_remaining
            )

            place_funded_orders(
                current_date,
                day_recommendations,
                open_orders,
                sku_lookup
            )

            recommendations.extend(
                day_recommendations
            )

            rows = create_daily_stock_rows(
                current_date,
                sku_lookup,
                opening_stock,
                stock,
                open_orders,
                result
            )

            daily_rows.extend(
                rows
            )

        elif command_name == "PRINT_CLASSIFICATION":
            print_classification(
                list(sku_lookup.values())
            )

        elif command_name == "PRINT_SEASONAL_INDICES":
            print_seasonal_indices(
                seasonal_indices
            )

        elif command_name == "PRINT_RECOMMENDATIONS":
            print_recommendations(
                recommendations
            )

        elif command_name == "PRINT_KPI":
            kpi_rows = build_kpi_report(
                daily_rows,
                skus
            )

            print_kpi(
                kpi_rows
            )

    return (
        daily_rows,
        recommendations,
        forecast_lookup,
        seasonal_indices,
        forecast_plans
    )

def main():
    print("Loading input data...")

    (
        suppliers,
        parameters,
        service_levels,
        skus,
        demand_history,
        opening_stock,
        open_orders,
        daily_demand,
        commands
    ) = load_data()

    sku_lookup = make_lookup(
        skus,
        "sku_id"
    )

    monthly_budget = float(
        get_parameter(
            parameters,
            "monthly_budget"
        )
    )

    shelf_life_usage = float(
        get_parameter(
            parameters,
            "shelf_life_usage"
        )
    )

    simulation_start = get_parameter(
        parameters,
        "simulation_start"
    )

    simulation_days = int(
        get_parameter(
            parameters,
            "simulation_end"
        )
    )

    if shelf_life_usage > 1:
        shelf_life_usage /= 100

    classification = build_classification(
        demand_history,
        skus,
        service_levels,
        simulation_start
    )

    for row in classification:
        sku_lookup[
            row["sku_id"]
        ].update(row)

    seasonal_indices = (
        calculate_seasonal_indices(
            demand_history
        )
    )

    forecast_lookup = {}
    forecast_plans = []

    stock = []

    for row in opening_stock:
        stock.append({
            "batch_id":
                row["batch_id"],
            "sku_id":
                row["sku_id"],
            "quantity":
                int(row["quantity"]),
            "received_date":
                row["received_date"]
        })

    open_orders_copy = []

    for row in open_orders:
        open_orders_copy.append({
            "po_id":
                row["po_id"],
            "sku_id":
                row["sku_id"],
            "quantity":
                int(row["quantity"]),
            "order_date":
                row["order_date"],
            "expected_receipt_date":
                row["expected_receipt_date"]
        })

    backorders = {}

    (
        daily_rows,
        recommendations,
        forecast_lookup,
        seasonal_indices,
        forecast_plans
    ) = process_commands(
        commands,
        sku_lookup,
        demand_history,
        skus,
        service_levels,
        daily_demand,
        stock,
        open_orders_copy,
        backorders,
        forecast_lookup,
        seasonal_indices,
        monthly_budget,
        shelf_life_usage
    )

    kpi_rows = build_kpi_report(
        daily_rows,
        skus
    )

    write_classification_report(
        classification
    )

    write_seasonal_indices_report(
        seasonal_indices
    )

    write_forecast_report(
        forecast_plans
    )

    write_recommendations_report(
        recommendations
    )

    write_daily_stock_report(
        daily_rows
    )

    write_kpi_report(
        kpi_rows
    )

    print()
    print("=" * 60)
    print("Simulation completed.")
    print("Output files created.")
    print("=" * 60)


if __name__ == "__main__":
    main()