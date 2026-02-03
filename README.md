# Gas-Fired Power Plant Optimization (MILP)

This repository contains a **mixed-integer linear programming (MILP)** model for optimizing the operating schedule of a gas-fired power plant under operational constraints and uncertain future prices.

---

## Problem Description

We model a gas-fired power plant operating in the period **December 31, 2021 – February 1, 2022**, after which the unit enters a long-term maintenance outage.

Given multiple simulated forward price scenarios for:

- Power (€/MWh)
- Gas (€/MWh)
- CO₂ (€/ton)

the objective is to **maximize total profit** while respecting strict operational constraints, including:

- Limited number of starts
- Limited total running hours
- Minimum and maximum generation levels
- Start-up costs and energy consumption depending on downtime duration

---

## Key Technical Parameters

- **Maximum capacity**: 400 MW  
- **Minimum stable generation**: 220 MW  
- **Remaining starts available**: 15  
- **Remaining running hours available**: 250  
- **Initial condition**: plant is running at the beginning of the horizon

### Start-up Types

Start-up behaviour and resource consumption depend on the number of hours the unit has been offline:

| Hours offline | Start Type | Power produced during start (MWh) | Gas consumed during start (MWh) | CO₂ emitted during start (t) |
|---------------|------------|------------------------------------|----------------------------------|-------------------------------|
| ≤ 10          | Type 1     | 75                                 | 190                              | 35                            |
| 11 – 35       | Type 2     | 190                                | 700                              | 130                           |
| > 35          | Type 3     | 210                                | 800                              | 150                           |

> Start-up energy, gas and CO₂ emissions are accounted for **in the hour before** the unit reaches minimum stable generation.

---

## Model Overview

The problem is formulated as a **Mixed-Integer Linear Program (MILP)** and solved using **PuLP + CBC solver**.

### Main Decision Variables

- `is_on[t]`               – binary: plant is producing power in hour t  
- `start[t]`               – binary: plant starts in hour t  
- `start_type_1[t]`, `start_type_2[t]`, `start_type_3[t]` – mutually exclusive start type indicators  
- `gen_above_min[t]`       – continuous: generation above minimum stable level (MW)  
- `consecutive_off_hours[t]` – auxiliary variable for tracking downtime  

### Objective Function

Maximize total profit over the horizon:

**Profit** = Power revenue − Gas cost − CO₂ cost

Revenue and cost terms include:

- Hourly generation revenue (including start-up power if credited)
- Start-up fuel and CO₂ costs
- Running fuel and CO₂ costs

---

