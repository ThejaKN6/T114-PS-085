import math


def calculate_cv(values):
    """
    Calculate population coefficient of variation.
    """

    mean = sum(values) / len(values)

    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / len(values)

    standard_deviation = math.sqrt(variance)

    if mean == 0:
        return 0

    return standard_deviation / mean


def get_last_months(
    demand_history,
    sku_id,
    as_of_date,
    number_of_months
):
    """
    Get the required number of history months
    ending at the as_of_date month.
    """

    as_of_month = as_of_date[:7]

    rows = [
        row
        for row in demand_history
        if row["sku_id"] == sku_id
        and row["month"] <= as_of_month
    ]

    rows.sort(
        key=lambda row: row["month"]
    )

    return rows[-number_of_months:]


def calculate_abc_xyz(
    demand_history,
    skus,
    service_levels,
    as_of_date
):
    """
    Calculate ABC + XYZ classification
    for every SKU.
    """

    results = []

    for sku in skus:

        sku_id = sku["sku_id"]

        history_12 = get_last_months(
            demand_history,
            sku_id,
            as_of_date,
            12
        )

        history_24 = get_last_months(
            demand_history,
            sku_id,
            as_of_date,
            24
        )

        annual_units = sum(
            float(row["units"])
            for row in history_12
        )

        annual_value = (
            annual_units
            * float(sku["unit_cost"])
        )

        values_24 = [
            float(row["units"])
            for row in history_24
        ]

        cv = calculate_cv(values_24)

        zero_months = sum(
            1
            for value in values_24
            if value == 0
        )

        if cv <= 0.5:
            xyz = "X"
        elif cv <= 1.0:
            xyz = "Y"
        else:
            xyz = "Z"

        results.append({
            "sku_id": sku_id,
            "annual_units": annual_units,
            "annual_value": annual_value,
            "cv": cv,
            "zero_months": zero_months,
            "xyz": xyz
        })

    return results

def add_abc_class(results):
    """
    Add ABC class using annual consumption value.

    A: cumulative share BEFORE the SKU < 70%
    B: cumulative share BEFORE the SKU < 90%
    C: otherwise
    """

    results.sort(
        key=lambda row: (
            -row["annual_value"],
            row["sku_id"]
        )
    )

    total_value = sum(
        row["annual_value"]
        for row in results
    )

    cumulative_value = 0

    for row in results:

        previous_share = (
            cumulative_value / total_value
            if total_value > 0
            else 0
        )

        if previous_share < 0.70:
            abc = "A"
        elif previous_share < 0.90:
            abc = "B"
        else:
            abc = "C"

        cumulative_value += row["annual_value"]

        row["abc"] = abc

        row["cum_share_pct"] = (
            cumulative_value
            / total_value
            * 100
            if total_value > 0
            else 0
        )

    return results


def add_service_levels(
    results,
    service_levels
):
    """
    Add class code, service level and z-value.
    """

    service_lookup = {
        row["class_code"]: row
        for row in service_levels
    }

    for row in results:

        class_code = (
            row["abc"] + row["xyz"]
        )

        service = service_lookup[
            class_code
        ]

        row["class_code"] = class_code

        row["service_level_pct"] = float(
            service["service_level_pct"]
        )

        row["z_value"] = float(
            service["z_value"]
        )

    return results


def build_classification(
    demand_history,
    skus,
    service_levels,
    as_of_date
):
    """
    Build the final classification table.
    """

    results = calculate_abc_xyz(
        demand_history,
        skus,
        service_levels,
        as_of_date
    )

    results = add_abc_class(results)

    results = add_service_levels(
        results,
        service_levels
    )

    return results