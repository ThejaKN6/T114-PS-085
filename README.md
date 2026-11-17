# T114-PS-085 Inventory Optimization Engine

## Project Overview

This project implements an inventory optimization and replenishment engine.

## Features

- ABC classification
- XYZ classification
- Seasonal index calculation
- Demand forecasting
- Safety stock calculation
- Reorder point calculation
- Daily inventory simulation
- FIFO stock consumption
- Backorder handling
- Lost sales handling
- Shelf-life expiry handling
- Budget-based replenishment
- KPI reporting

## Project Structure

PS085_Inventory_Engine/
│
├── data/
│   ├── commands.txt
│   ├── daily_demand.csv
│   ├── demand_history.csv
│   ├── open_orders.csv
│   ├── opening_stock.csv
│   ├── parameters.csv
│   ├── service_levels.csv
│   ├── skus.csv
│   └── suppliers.csv
│
├── outputs/
│   ├── classification.csv
│   ├── daily_stock.csv
│   ├── forecast_plan.csv
│   ├── kpi_report.csv
│   ├── recommendations.csv
│   └── seasonal_indices.csv
│
├── src/
│   ├── classification.py
│   ├── forecasting.py
│   ├── loader.py
│   ├── main.py
│   ├── reports.py
│   └── simulation.py
│
├── tests/
│   ├── conftest.py
│   └── test_engine.py
│
├── run_output.txt
└── README.md

## How to Run

Open the terminal in the project root directory and run:

python -m src.main

The program reads input files from the data directory and generates output files in the outputs directory.

## Testing

Run the test suite using:

pytest

## Business Rules

### ABC Classification

SKUs are ranked by annual inventory value.

- A class: cumulative annual value share below 70%
- B class: cumulative annual value share below 90%
- C class: remaining SKUs

An SKU exactly on the 70% cumulative boundary is classified as A.

### XYZ Classification

XYZ classification is based on the coefficient of variation (CV).

- X: CV <= 0.50
- Y: CV <= 1.00
- Z: CV > 1.00

### FIFO

Inventory is consumed using FIFO order based on receipt date.

### Backorders

For A and B items, unmet demand becomes a backorder and is fulfilled from the next available receipt.

### Lost Sales

For C items, unmet demand is treated as lost sales.

### Same-Day Receipt and Demand

When a receipt and demand occur on the same day, the receipt is processed first.

### Shelf Life

Inventory is expired when its age is greater than the configured shelf life.

### Budget

Replenishment recommendations are processed according to the defined priority and available monthly budget.

## Output Files

The system generates:

- classification.csv
- seasonal_indices.csv
- forecast_plan.csv
- recommendations.csv
- daily_stock.csv
- kpi_report.csv

## KPI Report

The KPI report contains:

- Units demanded
- Units shipped same day
- Fill rate
- Stock-out days
- Expired units
- Expired value
- Average inventory value

A TOTAL row is included in the KPI report.


[Watch the 5-Minute Demo Video]

https://drive.google.com/file/d/1svYjASR9ZNWj7ue-WYZeRjvyLc0WYMNf/view?usp=drivesdk
