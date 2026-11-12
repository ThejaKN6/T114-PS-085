T114-PS-085 Inventory Optimization Engine

Design Log

1. Purpose
This design log explains the main design decisions made while developing the Inventory Optimization Engine.
The project has several business rules, so some decisions had to be made about how those rules would be implemented in the code. This document records those decisions and briefly explains the reason behind each one.

2. Classification Design
Decision
The system uses ABC classification based on annual inventory value and XYZ classification based on demand variability.
Reason
Not every SKU has the same importance or demand behaviour. Some products have a much higher inventory value, while others have more unpredictable demand.
Because of this, using both ABC and XYZ classification gives a better view of each SKU.
ABC classification looks at annual inventory value, while XYZ classification looks at the variation in demand. The two results are then combined into a class code such as AX, BY or CZ.

3. ABC Boundary Decision
Decision
An SKU that reaches exactly 70% of the cumulative annual-value share is classified as A.
Reason
The project requirement specifies that the exact 70% boundary belongs to class A.
This means the implementation does not move an SKU into class B just because its cumulative value reaches exactly 70%.
This decision is important because the ABC class is later used in service-level and replenishment decisions.

4. XYZ Classification Decision
Decision
XYZ classification is based on the coefficient of variation calculated from the last 24 months of demand.
The thresholds used are:
- X: CV <= 0.50
- Y: CV <= 1.00
- Z: CV > 1.00
Reason
The coefficient of variation gives a useful way to measure how much demand changes compared with its average.
The last 24 months are used so that the calculation has enough historical data to represent the demand pattern of the SKU.

5. Seasonal Forecasting Decision
Decision
The forecast uses the average demand from the latest 12 months and applies the seasonal index of the forecast month.
Formula
Forecast Units = Average Demand of Last 12 Months × Seasonal Index
Reason
The recent 12-month average gives the basic demand level, while the seasonal index adjusts it according to the month.
This approach keeps the forecasting calculation simple while still considering seasonal changes in demand.

6. Safety Stock Decision
Decision
Safety stock is calculated using demand variability, lead time, lead-time variance and the service-level z-value.
Formula
Safety Stock = ceil(z × √(Lead Time × Daily Demand Variance + Daily Demand² × Lead-Time Variance))
Reason
Demand is not always predictable, and supplier lead times can also vary. Safety stock provides additional protection against this uncertainty.
There is also a special rule for Z items. If a Z item has at least three zero-demand months, the calculated safety stock is doubled.
This gives additional protection to items with highly variable demand and repeated zero-demand periods.

7. Reorder Point Decision
Decision
The system uses inventory position instead of looking only at the physical stock available.
Formula
Inventory Position = On-Hand Stock + On-Order Stock − Backorders
Reason
Looking only at on-hand stock can give an incomplete picture.
For example, an SKU may have low physical stock but already have a purchase order on the way. At the same time, an existing backorder means that some demand still needs to be fulfilled.
Therefore, the system considers both stock that is already on order and outstanding backorders.
A replenishment recommendation is generated when the inventory position is less than or equal to the reorder point.

8. FIFO Design Decision
Decision
Inventory is consumed using FIFO based on the received date of each stock batch.
Reason
FIFO means that the oldest available stock is used first.
This is particularly useful for this project because inventory also has shelf-life restrictions. Using older stock first helps reduce the chance of older inventory remaining unused until it expires.
The system therefore works with individual inventory batches instead of treating all stock of an SKU as one quantity.

9. Backorder Design Decision
Decision
When A and B items do not have enough stock to satisfy demand, the remaining quantity is recorded as a backorder.
Reason
A and B items have higher priority in the inventory policy. Therefore, their unmet demand should continue to be tracked instead of immediately being treated as lost sales.
When a new receipt arrives, the system first uses that receipt to fulfil the existing backorder.
If the receipt is smaller than the backorder, only part of the backorder is fulfilled. The remaining quantity stays as an outstanding backorder.

10. Lost Sales Design Decision
Decision
Unmet demand for C items is treated as lost sales.
Reason
The business rules specify different treatment for C items.
Unlike A and B items, the unmet quantity for a C item is not carried forward as a backorder.
For example, if a C item has demand of 100 units but only 70 units are available, 70 units are shipped and the remaining 30 units are recorded as lost sales.

11. Same-Day Receipt Decision
Decision
When a receipt and demand happen on the same day, the receipt is processed first.
Reason
If stock reaches the warehouse on a particular day, that stock should be available for that day's demand.
This also gives the daily simulation a fixed processing order and avoids ambiguity when both events have the same date.

12. Shelf-Life Design Decision
Decision
A stock batch expires when its age becomes greater than the configured shelf life.
Age > Shelf Life → Expired
If the age is exactly equal to the shelf life, the stock is still considered valid.
Reason
This follows the shelf-life rule selected for the project.
The system checks the age of each individual batch using its received date. This is more appropriate than applying shelf life to the total SKU quantity because different batches can have different ages.

13. Shelf-Life Replenishment Decision
Decision
The recommended order quantity is checked against the quantity that can reasonably be consumed within the available shelf-life period.
If the shelf-life cap is below MOQ, the recommendation is rejected.
The result is:
Decision: REJECTED
Reason: SHELF_LIFE
Reason
There is little benefit in ordering a quantity that cannot realistically be consumed before it reaches its shelf-life limit.
Therefore, the shelf-life check is performed before the budget decision.
This prevents an order from being funded when the quantity itself is not suitable from a shelf-life point of view.

14. Order Quantity Decision
Decision
The order quantity depends on the ABC class.
For A and B items:
Order Quantity = max(ceil(EOQ), MOQ)
For C items:
Order Quantity = max(ceil(3 × Forecast Units), MOQ)
After this calculation, the final quantity is adjusted to the required pack-size multiple.
Reason
A and B items use an EOQ-based approach, while C items use a forecast-based quantity.
MOQ is considered because the supplier may require a minimum order quantity.
Pack-size adjustment is then applied because the final order quantity should match the required packaging multiple.

15. Budget Allocation Decision
Decision
Replenishment recommendations are prioritised using the following class order:
A → B → C
Days of cover are also considered when ordering recommendations.
Reason
The monthly budget may not be enough to fund every recommendation. Because of this, higher-priority items should be considered before lower-priority items.
If the order value is within the remaining budget, the recommendation is marked as FUNDED.
If the order value is greater than the remaining budget, it is marked as DEFERRED with the reason BUDGET.

16. Exact Budget Boundary
Decision
An order is funded when its value is exactly equal to the remaining budget.
Reason
The budget comparison allows the order value to be equal to the amount still available.
For example, if ₹50,000 is remaining and the order value is exactly ₹50,000, the order can still be funded.
This avoids incorrectly rejecting an order when the available budget is sufficient to cover it exactly.

17. Supplier and Purchase Order Design
Decision
A funded replenishment recommendation is converted into an automatic purchase order.
The expected receipt date is calculated using the lead time.
Formula
Expected Receipt Date = Order Date + Lead Time
Reason
This connects the replenishment recommendation with the actual inventory simulation.
Once the expected receipt date is reached, the purchase order is processed as a receipt and becomes part of the inventory flow.
This allows the order created by the replenishment logic to directly affect future stock availability.

18. KPI Design
Decision
The system generates KPI results for every SKU and also includes a TOTAL row.
The main KPIs are:
Units demanded
Units shipped same day
Fill rate
Stock-out days
Expired units
Expired value
Average inventory value
Reason
SKU-level results help identify which products performed well or poorly during the simulation.
The TOTAL row gives an overall view of the inventory system.
The fill rate is calculated as:
Fill Rate = Units Shipped Same Day / Units Demanded × 100
If there is no demand, the system reports a fill rate of 100%.

19. Testing Design
Decision
The implementation is tested against important business-rule edge cases instead of checking only whether the program runs successfully.
The important cases include:
Exact 70% ABC boundary
Zero-demand months
EOQ below MOQ
MOQ not matching pack size
Shelf-life cap below MOQ
Exact remaining budget
Same-day receipt and demand
Zero lead-time variance
Partial backorder fulfilment
Reason
These cases are important because a small change in the logic can change the final output.
For example, changing the 70% comparison, processing demand before a same-day receipt, or handling a partial backorder incorrectly can produce different results from the required output.
Testing these cases helps confirm that the implementation follows the defined business rules.

20. Overall Design Approach
The project separates the calculation part from the daily simulation part.
Classification and forecasting calculations are completed before the daily simulation. The simulation then uses these calculated values to make replenishment decisions.
The daily simulation follows a fixed sequence:
1. Expire stock.
2. Receive due orders.
3. Fulfil existing backorders.
4. Process demand.
5. Consume stock using FIFO.
6. Create backorders or record lost sales.
7. Generate replenishment recommendations.
8. Apply shelf-life rules.
9. Apply the available budget.
10. Create funded purchase orders.
Keeping this sequence fixed makes the daily processing easier to follow and ensures that events happen in the intended order.

21. Final Design Summary
The main idea behind the design is to make replenishment decisions using both demand information and practical inventory constraints.
The system does not depend on one calculation alone. Classification helps identify the importance and demand behaviour of each SKU. Forecasting estimates future demand, safety stock provides protection against uncertainty, and the reorder point identifies when replenishment may be required.
The order-quantity logic then considers EOQ, MOQ and pack size. During the daily simulation, the system applies FIFO, handles backorders and lost sales, checks shelf life, and finally applies the available budget before creating purchase orders.
The final reports provide a detailed view of the inventory movement and the overall performance of the simulation.
This design keeps the main business rules clearly separated while allowing them to work together as one inventory optimization process.
