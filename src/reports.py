import csv


def format_value(value, fieldname):
    """
    Format output values according to the project rules.
    """

    if value is None:
        return ""

    integer_fields = (
        "annual_units",
        "zero_months",
        "month_no",
        "forecast_units",
        "safety_stock",
        "reorder_point",
        "order_qty",
        "shelf_cap",
        "inventory_position",
        "stockout_days",
        "expired_units",
        "units_demanded",
        "units_shipped_same_day",
        "backordered",
        "lost",
        "shipped",
        "demand",
        "opening_on_hand",
        "closing_on_hand",
        "on_order",
        "backorder_balance",
        "expired",
        "received",
        "backorder_filled"
    )

    decimal_fields = (
        "annual_value",
        "eoq",
        "order_value",
        "expired_value",
        "avg_inventory_value"
    )

    percentage_fields = (
        "cum_share_pct",
        "cv",
        "service_level_pct",
        "z_value",
        "seasonal_index",
        "daily_demand",
        "fill_rate_pct",
        "budget_remaining_after",
        "days_of_cover"
    )

    if fieldname in integer_fields:
        return str(int(round(float(value))))

    if fieldname in decimal_fields:
        return f"{float(value):.2f}"

    if fieldname in percentage_fields:
        return f"{float(value):.2f}"

    return str(value)


def write_csv(filename, rows, fieldnames):

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for row in rows:

            formatted_row = {}

            for fieldname in fieldnames:
                formatted_row[fieldname] = format_value(
                    row.get(fieldname),
                    fieldname
                )

            writer.writerow(formatted_row)


def write_classification_report(rows):

    fieldnames = [
        "sku_id",
        "annual_units",
        "annual_value",
        "cum_share_pct",
        "abc",
        "cv",
        "xyz",
        "zero_months",
        "class_code",
        "service_level_pct",
        "z_value"
    ]

    write_csv(
        "outputs/classification.csv",
        rows,
        fieldnames
    )


def write_seasonal_indices_report(rows):

    fieldnames = [
        "sku_id",
        "month_no",
        "seasonal_index"
    ]

    write_csv(
        "outputs/seasonal_indices.csv",
        rows,
        fieldnames
    )


def write_forecast_report(rows):

    fieldnames = [
        "sku_id",
        "month",
        "forecast_units",
        "daily_demand",
        "safety_stock",
        "reorder_point",
        "eoq",
        "order_qty",
        "shelf_cap"
    ]

    write_csv(
        "outputs/forecast_plan.csv",
        rows,
        fieldnames
    )


def write_recommendations_report(rows):

    fieldnames = [
        "date",
        "sku_id",
        "class_code",
        "inventory_position",
        "reorder_point",
        "days_of_cover",
        "order_qty",
        "order_value",
        "consolidated",
        "decision",
        "reason",
        "budget_remaining_after"
    ]

    write_csv(
        "outputs/recommendations.csv",
        rows,
        fieldnames
    )


def write_daily_stock_report(rows):

    fieldnames = [
        "date",
        "sku_id",
        "opening_on_hand",
        "expired",
        "received",
        "backorder_filled",
        "demand",
        "shipped",
        "backordered",
        "lost",
        "closing_on_hand",
        "on_order",
        "backorder_balance"
    ]

    write_csv(
        "outputs/daily_stock.csv",
        rows,
        fieldnames
    )


def write_kpi_report(rows):

    fieldnames = [
        "sku_id",
        "units_demanded",
        "units_shipped_same_day",
        "fill_rate_pct",
        "stockout_days",
        "expired_units",
        "expired_value",
        "avg_inventory_value"
    ]

    write_csv(
        "outputs/kpi_report.csv",
        rows,
        fieldnames
    )