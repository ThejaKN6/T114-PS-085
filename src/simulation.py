from datetime import datetime, timedelta
import math


def to_date(value):
    """
    Convert a date value into a date object.
    Accepts both YYYY-MM-DD and YYYY/MM/DD.
    """

    if value == "":
        return None

    if isinstance(value, str):

        value = value.strip()

        for date_format in (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y/%m/%d"
        ):
            try:
                return datetime.strptime(
                    value,
                    date_format
                ).date()
            except ValueError:
                continue

    return value


def get_inventory_position(
    stock,
    open_orders,
    backorders,
    sku_id
):
    """
    Inventory position =
    on-hand stock + on-order stock - backorders
    """

    on_hand = sum(
        item["quantity"]
        for item in stock
        if item["sku_id"] == sku_id
    )

    on_order = sum(
        int(order["quantity"])
        for order in open_orders
        if order["sku_id"] == sku_id
    )

    backorder = backorders.get(
        sku_id,
        0
    )

    return (
        on_hand
        + on_order
        - backorder
    )


def get_stock_quantity(
    sku_id,
    stock
):
    """
    Get total stock quantity for one SKU.
    """

    total = 0

    for item in stock:

        if item["sku_id"] == sku_id:
            total += int(item["quantity"])

    return total


def save_opening_stock(
    sku_lookup,
    stock
):
    """
    Save current stock quantity
    for every SKU.
    """

    opening_stock = {}

    for sku_id in sku_lookup:

        opening_stock[sku_id] = get_stock_quantity(
            sku_id,
            stock
        )

    return opening_stock

def expire_stock(
    current_date,
    stock,
    sku_lookup
):
    """
    Remove stock whose age is greater
    than its shelf life.
    """

    expired = {}

    remaining_stock = []

    for batch in stock:

        sku = batch["sku_id"]

        shelf_life = int(
            sku_lookup[sku]["shelf_life_days"]
        )

        

        received_date = to_date(
            batch["received_date"]
        )

        # Ignore batches with no received date
        if received_date is None:
            remaining_stock.append(batch)
            continue
        
        if shelf_life == 0:
            remaining_stock.append(batch)
            continue

        age = (
            current_date - received_date
        ).days

        if age > shelf_life:

            quantity = int(
                batch["quantity"]
            )

            expired[sku] = (
                expired.get(sku, 0)
                + quantity
            )

            continue

        remaining_stock.append(batch)

    stock[:] = remaining_stock

    return expired


def receive_orders(
    current_date,
    stock,
    open_orders,
    backorders
):
    """
    Receive orders due today.
    Fill old backorders first.
    """

    received = {}
    filled = {}

    remaining_orders = []

    for order in open_orders:

        receipt_date = to_date(
            order["expected_receipt_date"]
        )

        if receipt_date != current_date:

            remaining_orders.append(
                order
            )

            continue

        sku = order["sku_id"]

        quantity = int(
            order["quantity"]
        )

        received[sku] = (
            received.get(sku, 0)
            + quantity
        )

        old_backorder = backorders.get(
            sku,
            0
        )

        used = min(
            quantity,
            old_backorder
        )

        if used > 0:

            backorders[sku] -= used

            quantity -= used

            filled[sku] = (
                filled.get(sku, 0)
                + used
            )

        # Remaining quantity becomes stock
        if quantity > 0:

            stock.append({
                "batch_id":
                    "RECEIPT-" + order["po_id"],

                "sku_id":
                    sku,

                "quantity":
                    quantity,

                "received_date":
                    current_date
            })

    open_orders[:] = remaining_orders

    return received, filled

def process_demand(
    current_date,
    daily_demand,
    stock,
    backorders,
    sku_lookup
):
    """
    Process demand for one day.

    A/B items become backorders when stock is insufficient.
    C items become lost sales.
    """

    demand = {}
    shipped = {}
    backordered = {}
    lost = {}

    daily_rows = {}

    for row in daily_demand:

        demand_date = to_date(
            row["date"]
        )

        if demand_date != current_date:
            continue

        sku = row["sku_id"]

        # Ignore duplicate date + SKU rows
        if sku in daily_rows:
            continue

        daily_rows[sku] = int(
            row["units"]
        )
        
            

    for sku, units in daily_rows.items():

        demand[sku] = units

        remaining = units

        batches = [
            item
            for item in stock
            if (
                item["sku_id"] == sku
                and item["quantity"] > 0
            )
        ]

        # FIFO: oldest stock first
        batches.sort(
            key=lambda item:
            to_date(item["received_date"])
            if item["received_date"]
            else current_date
        )

        for batch in batches:

            if remaining <= 0:
                break

            shipped_units = min(
                batch["quantity"],
                remaining
            )

            batch["quantity"] -= (
                shipped_units
            )

            remaining -= shipped_units

            shipped[sku] = (
                shipped.get(sku, 0)
                + shipped_units
            )

        # Demand that could not be shipped
        if remaining > 0:

            abc = sku_lookup[sku]["abc"]

            if abc in ("A", "B"):

                backorders[sku] = (
                    backorders.get(sku, 0)
                    + remaining
                )

                backordered[sku] = (
                    backordered.get(sku, 0)
                    + remaining
                )

            else:

                lost[sku] = (
                    lost.get(sku, 0)
                    + remaining
                )

    return (
        demand,
        shipped,
        backordered,
        lost
    )


def simulate_day(
    current_date,
    daily_demand,
    stock,
    open_orders,
    backorders,
    sku_lookup
):
    """
    Run one day of inventory simulation.

    Order:
    1. Expire stock
    2. Receive orders
    3. Process demand
    """

    expired = expire_stock(
        current_date,
        stock,
        sku_lookup
    )

    received, backorder_filled = receive_orders(
        current_date,
        stock,
        open_orders,
        backorders
    )

    demand, shipped, backordered, lost = (
        process_demand(
            current_date,
            daily_demand,
            stock,
            backorders,
            sku_lookup
        )
    )

    backorder_balance = {}

    for sku_id in sku_lookup:

        backorder_balance[sku_id] = (
            backorders.get(
                sku_id,
                0
            )
        )

    return {
        "expired": expired,
        "received": received,
        "backorder_filled":
            backorder_filled,
        "demand": demand,
        "shipped": shipped,
        "backordered": backordered,
        "lost": lost,
        "backorder_balance":
            backorder_balance
    }

def add_reorder_to_day(
    current_date,
    sku_lookup,
    stock,
    open_orders,
    backorders,
    forecast_lookup
):
    """
    Check all SKUs for reorder.
    """

    recommendations = []

    for sku_id in sku_lookup:

        forecast = forecast_lookup.get(
            sku_id
        )

        if forecast is None:
            continue

        inventory_position = get_inventory_position(
            stock,
            open_orders,
            backorders,
            sku_id
        )

        reorder_point = forecast[
            "reorder_point"
        ]

        order_qty = forecast[
            "order_qty"
        ]

        daily_demand = forecast[
            "daily_demand"
        ]

        if daily_demand > 0:
            days_of_cover = (
                inventory_position
                / daily_demand
            )
        else:
            days_of_cover = 999999

        if inventory_position <= reorder_point:

            recommendations.append({
                "date": current_date,
                "sku_id": sku_id,
                "class_code": sku_lookup[
                    sku_id
                ]["class_code"],
                "inventory_position":
                    inventory_position,
                "reorder_point":
                    reorder_point,
                "days_of_cover":
                    days_of_cover,
                "order_qty":
                    order_qty
            })

    return recommendations


def apply_shelf_life_rule(
    recommendation,
    sku_info,
    forecast,
    shelf_life_usage
):
    """
    Apply the shelf-life restriction
    to one reorder recommendation.
    """

    shelf_life_days = int(
        sku_info["shelf_life_days"]
    )

    moq = int(
        sku_info["moq"]
    )

    pack_size = int(
        sku_info["pack_size"]
    )

    daily_demand = float(
        forecast["daily_demand"]
    )

    order_qty = int(
        recommendation["order_qty"]
    )

    # No shelf-life restriction
    if shelf_life_days <= 0:
        return recommendation

    shelf_cap = math.floor(
        daily_demand
        * shelf_life_usage
        * shelf_life_days
    )

    recommendation["shelf_cap"] = (
        shelf_cap
    )

    # Shelf-life cap is below MOQ
    if shelf_cap < moq:

        recommendation["decision"] = (
            "REJECTED"
        )

        recommendation["reason"] = (
            "SHELF_LIFE"
        )

        return recommendation

    # Reduce order quantity to shelf cap
    order_qty = min(
        order_qty,
        shelf_cap
    )

    # Round DOWN to pack size
    order_qty = (
        math.floor(
            order_qty / pack_size
        )
        * pack_size
    )

    # Rounded quantity is below MOQ
    if order_qty < moq:

        recommendation["decision"] = (
            "REJECTED"
        )

        recommendation["reason"] = (
            "SHELF_LIFE"
        )

        return recommendation

    recommendation["order_qty"] = (
        order_qty
    )

    return recommendation

def apply_budget(
    recommendations,
    monthly_budget,
    budget_used
):
    """
    Fund recommendations by priority.

    A before B before C.
    Within each class, lowest days of cover first.
    Rejected recommendations are handled last.
    """

    remaining_budget = (
        monthly_budget
        - budget_used
    )

    class_priority = {
        "A": 1,
        "B": 2,
        "C": 3
    }

    recommendations.sort(
        key=lambda row: (
            row.get("decision") == "REJECTED",
            class_priority[row["class_code"][0]],
            row["days_of_cover"]
        )
    )

    for recommendation in recommendations:

        order_value = (
            recommendation["order_qty"]
            * recommendation["unit_cost"]
        )

        recommendation["order_value"] = (
            order_value
        )

        if recommendation.get("decision") == "REJECTED":

            recommendation[
                "budget_remaining_after"
            ] = remaining_budget

            continue

        if order_value <= remaining_budget:

            recommendation["decision"] = "FUNDED"
            recommendation["reason"] = "REORDER"

            remaining_budget -= order_value

        else:

            recommendation["decision"] = "DEFERRED"
            recommendation["reason"] = "BUDGET"

        recommendation[
            "budget_remaining_after"
        ] = remaining_budget

    return remaining_budget

def process_recommendations(
    recommendations,
    sku_lookup,
    forecast_lookup,
    monthly_budget,
    budget_used,
    shelf_life_usage
):
    """
    Apply shelf-life,
    supplier consolidation,
    and budget rules.
    """

    processed = []

    # 1. Apply shelf-life rule
    for recommendation in recommendations:

        sku_id = recommendation["sku_id"]

        sku_info = sku_lookup[sku_id]
        forecast = forecast_lookup[sku_id]

        recommendation = apply_shelf_life_rule(
            recommendation,
            sku_info,
            forecast,
            shelf_life_usage
        )

        recommendation["unit_cost"] = float(
            sku_info["unit_cost"]
        )

        recommendation.setdefault(
            "consolidated",
            False
        )

        processed.append(recommendation)

    # 2. Group by supplier
    supplier_groups = {}

    for recommendation in processed:

        if recommendation.get("decision") == "REJECTED":
            continue

        sku_id = recommendation["sku_id"]

        supplier_id = sku_lookup[sku_id]["supplier_id"]

        supplier_groups.setdefault(
            supplier_id,
            []
        ).append(recommendation)

    # 3. Supplier consolidation
    #
    # Only increase a recommendation when
    # the consolidated order still fits
    # within the available budget.

    remaining_budget = (
        monthly_budget - budget_used
    )

    for group in supplier_groups.values():

        if len(group) < 2:
            continue

        largest = max(
            group,
            key=lambda row:
            row["order_qty"] * row["unit_cost"]
        )

        for recommendation in group:

            if recommendation is largest:
                continue

            sku_id = recommendation["sku_id"]

            sku = sku_lookup[sku_id]
            forecast = forecast_lookup[sku_id]

            target_quantity = (
                forecast["reorder_point"]
                + forecast["eoq"]
                - recommendation["inventory_position"]
            )

            target_quantity = max(
                target_quantity,
                recommendation["order_qty"]
            )

            pack_size = int(
                sku["pack_size"]
            )

            target_quantity = (
                math.ceil(
                    target_quantity / pack_size
                ) * pack_size
            )

            target_value = (
                target_quantity
                * recommendation["unit_cost"]
            )

            if target_value <= remaining_budget:

                recommendation["order_qty"] = int(
                    target_quantity
                )

                recommendation["consolidated"] = True
    if processed and str(processed[0]["date"]) == "2026-10-01":
        print("OCTOBER 1 BEFORE BUDGET:")
        for r in processed:
            print(
                r["sku_id"],
                r["class_code"],
                r["days_of_cover"],
                r["order_qty"],
                r["order_qty"] * r["unit_cost"]
            )
    # 4. Apply budget
    remaining_budget = apply_budget(
        processed,
        monthly_budget,
        budget_used
    )

    # Remove temporary fields
    for recommendation in processed:

        recommendation.pop(
            "unit_cost",
            None
        )

        recommendation.pop(
            "shelf_cap",
            None
        )

    return (
        processed,
        remaining_budget
    )

def place_funded_orders(
    current_date,
    recommendations,
    open_orders,
    sku_lookup
):
    """
    Add funded orders to open orders.
    """

    for recommendation in recommendations:

        if recommendation.get(
            "decision"
        ) != "FUNDED":
            continue

        sku_id = recommendation[
            "sku_id"
        ]

        quantity = int(
            recommendation["order_qty"]
        )

        lead_time = int(
            sku_lookup[sku_id][
                "lead_time_days"
            ]
        )

        receipt_date = (
            current_date
            + timedelta(days=lead_time)
        )

        po_id = (
            "AUTO-"
            + current_date.strftime(
                "%Y%m%d"
            )
            + "-"
            + sku_id
        )

        open_orders.append({
            "po_id": po_id,
            "sku_id": sku_id,
            "quantity": quantity,
            "order_date": current_date,
            "expected_receipt_date":
                receipt_date
        })


def create_daily_stock_rows(
    current_date,
    sku_lookup,
    opening_stock,
    stock,
    open_orders,
    result
):
    """
    Create one daily stock row
    for every SKU.
    """

    rows = []

    for sku_id in sku_lookup:

        opening_on_hand = int(
            opening_stock.get(
                sku_id,
                0
            )
        )

        expired = int(
            result["expired"].get(
                sku_id,
                0
            )
        )

        received = int(
            result["received"].get(
                sku_id,
                0
            )
        )

        backorder_filled = int(
            result["backorder_filled"].get(
                sku_id,
                0
            )
        )

        demand = int(
            result["demand"].get(
                sku_id,
                0
            )
        )

        shipped = int(
            result["shipped"].get(
                sku_id,
                0
            )
        )

        backordered = int(
            result["backordered"].get(
                sku_id,
                0
            )
        )

        lost = int(
            result["lost"].get(
                sku_id,
                0
            )
        )

        closing_on_hand = get_stock_quantity(
            sku_id,
            stock
        )

        on_order = sum(
            int(order["quantity"])
            for order in open_orders
            if order["sku_id"] == sku_id
        )

        backorder_balance = int(
            result["backorder_balance"].get(
                sku_id,
                0
            )
        )

        rows.append({
            "date": current_date,
            "sku_id": sku_id,
            "opening_on_hand":
                opening_on_hand,
            "expired":
                expired,
            "received":
                received,
            "backorder_filled":
                backorder_filled,
            "demand":
                demand,
            "shipped":
                shipped,
            "backordered":
                backordered,
            "lost":
                lost,
            "closing_on_hand":
                closing_on_hand,
            "on_order":
                on_order,
            "backorder_balance":
                backorder_balance
        })

    return rows

def run_simulation(
    start_date,
    days,
    daily_demand,
    stock,
    open_orders,
    backorders,
    sku_lookup,
    forecast_lookup,
    monthly_budget,
    shelf_life_usage
):
    """
    Run the inventory simulation day by day.
    """

    daily_rows = []
    recommendations = []

    current_date = to_date(
        start_date
    )

    budget_used = 0

    opening_stock = save_opening_stock(
        sku_lookup,
        stock
    )

    for day in range(days):

        # Reset monthly budget
        if current_date.day == 1:
            budget_used = 0

        # 1. Expire stock
        # 2. Receive orders
        # 3. Process demand
        result = simulate_day(
            current_date,
            daily_demand,
            stock,
            open_orders,
            backorders,
            sku_lookup
        )

        # 4. Check reorder requirements
        day_recommendations = (
            add_reorder_to_day(
                current_date,
                sku_lookup,
                stock,
                open_orders,
                backorders,
                forecast_lookup
            )
        )

        # 5. Apply shelf-life,
        #    consolidation and budget
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

        # Calculate budget used
        budget_used = (
            monthly_budget
            - budget_remaining
        )

        # 6. Place funded orders
        place_funded_orders(
            current_date,
            day_recommendations,
            open_orders,
            sku_lookup
        )

        # 7. Save recommendations
        recommendations.extend(
            day_recommendations
        )

        # 8. Create daily stock rows
        rows = create_daily_stock_rows(
            current_date,
            sku_lookup,
            opening_stock,
            stock,
            open_orders,
            result
        )

        daily_rows.extend(rows)

        # 9. Save current stock
        #    for the next day
        opening_stock = save_opening_stock(
            sku_lookup,
            stock
        )

        # 10. Move to next day
        current_date += timedelta(
            days=1
        )

    return (
        daily_rows,
        recommendations
    )

