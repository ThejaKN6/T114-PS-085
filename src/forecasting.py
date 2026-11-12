import math


def calculate_seasonal_indices(demand_history):
    """
    Calculate seasonal index for each SKU
    and calendar month.
    """

    sku_data = {}

    for row in demand_history:

        sku_id = row["sku_id"]
        month_no = int(row["month"].split("-")[1])
        units = float(row["units"])

        if sku_id not in sku_data:
            sku_data[sku_id] = []

        sku_data[sku_id].append(
            (month_no, units)
        )

    results = []

    for sku_id, values in sku_data.items():

        overall_average = (
            sum(units for _, units in values)
            / len(values)
        )

        for month_no in range(1, 13):

            month_values = [
                units
                for month, units in values
                if month == month_no
            ]

            if overall_average == 0:
                seasonal_index = 1.0

            else:
                month_average = (
                    sum(month_values)
                    / len(month_values)
                )

                seasonal_index = (
                    month_average
                    / overall_average
                )

            results.append({
                "sku_id": sku_id,
                "month_no": month_no,
                "seasonal_index": seasonal_index
            })

    return results


def calculate_forecast_units(
    demand_history,
    seasonal_indices,
    sku_id,
    forecast_month
):
    """
    Calculate forecast units for one SKU.
    """

    history = [
        row
        for row in demand_history
        if row["sku_id"] == sku_id
    ]

    history.sort(
        key=lambda row: row["month"]
    )

    last_12 = history[-12:]

    average_demand = (
        sum(
            float(row["units"])
            for row in last_12
        )
        / len(last_12)
    )

    month_no = int(
        forecast_month.split("-")[1]
    )

    seasonal_index = next(
        row["seasonal_index"]
        for row in seasonal_indices
        if (
            row["sku_id"] == sku_id
            and row["month_no"] == month_no
        )
    )

    return (
        average_demand
        * seasonal_index
    )


def calculate_safety_stock(
    demand_history,
    sku_id,
    daily_demand,
    lead_time_days,
    lead_time_var_days2,
    z_value,
    xyz
):
    """
    Calculate safety stock.
    """

    history = [
        row
        for row in demand_history
        if row["sku_id"] == sku_id
    ]

    history.sort(
        key=lambda row: row["month"]
    )

    last_24 = history[-24:]

    values = [
        float(row["units"])
        for row in last_24
    ]

    mean = (
        sum(values)
        / len(values)
    )

    variance = (
        sum(
            (value - mean) ** 2
            for value in values
        )
        / len(values)
    )

    daily_variance = (
        variance / 30
    )

    safety_stock = math.ceil(
        z_value
        * math.sqrt(
            lead_time_days
            * daily_variance
            +
            (
                daily_demand ** 2
                * lead_time_var_days2
            )
        )
    )

    zero_months = sum(
        1
        for value in values
        if value == 0
    )

    if xyz == "Z" and zero_months >= 3:
        safety_stock *= 2

    return safety_stock


def calculate_reorder_point(
    daily_demand,
    lead_time_days,
    safety_stock
):
    """
    Calculate reorder point.
    """

    return math.ceil(
        daily_demand
        * lead_time_days
        + safety_stock
    )


def calculate_order_quantity(
    abc,
    forecast_units,
    eoq,
    moq,
    pack_size
):
    """
    Calculate order quantity.
    """

    if abc in ("A", "B"):

        quantity = max(
            math.ceil(eoq),
            moq
        )

    else:

        quantity = max(
            math.ceil(
                3 * forecast_units
            ),
            moq
        )

    quantity = (
        math.ceil(
            quantity / pack_size
        )
        * pack_size
    )

    return quantity


def calculate_eoq(
    forecast_units,
    unit_cost,
    ordering_cost,
    holding_cost_percent
):
    """
    Calculate EOQ.
    """

    holding_cost = (
        unit_cost
        * holding_cost_percent
        / 100
    )

    if holding_cost == 0:
        return 0

    return math.sqrt(
        (
            2
            * forecast_units
            * ordering_cost
        )
        / holding_cost
    )