import pandas as pd
import pulp


def solve_one_simulation(power_price, gas_price, co2_price, num_simulation, out_dir="data/output"):
    n_hours = len(power_price)

    MAX_CAP = 400
    MIN_CAP = 220
    MAX_STARTS = 15
    MAX_RUN_HOURS = 250

    start_types = {
        1: {"gas": 190, "co2": 35, "power": 75},   # <=10 hours off
        2: {"gas": 700, "co2": 130, "power": 190}, # 11-35 hours off
        3: {"gas": 800, "co2": 150, "power": 210}, # >35 hours off
    }

    model = pulp.LpProblem(f"gas_plant_sim_{num_simulation}", pulp.LpMaximize)

    # Decision variables
    is_on = pulp.LpVariable.dicts("is_on", range(n_hours), lowBound=0, upBound=1, cat="Binary")
    start = pulp.LpVariable.dicts("start", range(n_hours), lowBound=0, upBound=1, cat="Binary")

    start_type_1 = pulp.LpVariable.dicts("start_type_1", range(n_hours), lowBound=0, upBound=1, cat="Binary")
    start_type_2 = pulp.LpVariable.dicts("start_type_2", range(n_hours), lowBound=0, upBound=1, cat="Binary")
    start_type_3 = pulp.LpVariable.dicts("start_type_3", range(n_hours), lowBound=0, upBound=1, cat="Binary")

    gen_above_min = pulp.LpVariable.dicts("gen_above_min_mw", range(n_hours), lowBound=0, upBound=MAX_CAP - MIN_CAP, cat="Continuous")

    gas_in_mwh = pulp.LpVariable.dicts("gas_in_mwh", range(n_hours), lowBound=0, cat="Continuous")
    co2_ton = pulp.LpVariable.dicts("co2_ton", range(n_hours), lowBound=0, cat="Continuous")

    consecutive_off_hours = pulp.LpVariable.dicts("consecutive_off_hours", range(n_hours), lowBound=0, upBound=n_hours, cat="Integer")

    # Initial condition: plant is running on December 31st
    print("Creating constraints...")
    model += is_on[0] == 1
    model += start[0] == 0
    model += consecutive_off_hours[0] == 0

    BIG_M = n_hours # + small int (defensive padding)

    for hour in range(n_hours):
        # Generation: if ON then at least MIN_CAP (up to MAX_CAP), if OFF then 0
        model += gen_above_min[hour] <= (MAX_CAP - MIN_CAP) * is_on[hour]

        # Fuel consumption: MIN_CAP part at eff 0.45, above MIN_CAP at eff 0.5
        model += gas_in_mwh[hour] == (MIN_CAP * (1.0 / 0.45)) * is_on[hour] + (1.0 / 0.5) * gen_above_min[hour]

        # CO2 production: 0.2 ton per 1 MWh gas
        model += co2_ton[hour] == 0.2 * gas_in_mwh[hour]

        # Start definition
        if hour >= 1:
            # start[hour] = 1 <-> (is_on[hour] = 1 and is_on[hour-1] = 0)
            # <--
            model += start[hour] >= is_on[hour] - is_on[hour - 1]
            # -->
            model += start[hour] <= is_on[hour]
            model += start[hour] <= 1 - is_on[hour - 1]

        # consecutive_off_hours tracking
        # If is_on[hour]=1 then consecutive_off[hour]=0, else consecutive_off[hour]=consecutive_off[hour-1]+1
        if hour >= 1:
            model += consecutive_off_hours[hour] <= consecutive_off_hours[hour - 1] + 1
            model += consecutive_off_hours[hour] <= BIG_M * (1 - is_on[hour])
            model += consecutive_off_hours[hour] >= (consecutive_off_hours[hour - 1] + 1) - BIG_M * is_on[hour]
        else:
            model += consecutive_off_hours[hour] == 0

        # Only one start type
        model += start_type_1[hour] + start_type_2[hour] + start_type_3[hour] == start[hour]

        if hour >= 1:
            off_before = consecutive_off_hours[hour - 1]

            # type 1: off_before <= 10
            model += off_before <= 10 + BIG_M * (1 - start_type_1[hour])

            # type 2: 11 <= off_before <= 35
            model += off_before >= 11 - BIG_M * (1 - start_type_2[hour])
            model += off_before <= 35 + BIG_M * (1 - start_type_2[hour])

            # type 3: off_before >= 36
            model += off_before >= 36 - BIG_M * (1 - start_type_3[hour])
        else:
            model += start_type_1[hour] == 0
            model += start_type_2[hour] == 0
            model += start_type_3[hour] == 0

    # Limit of starts and run hours
    model += pulp.lpSum(start[t] for t in range(n_hours)) <= MAX_STARTS
    model += pulp.lpSum(is_on[t] for t in range(n_hours)) <= MAX_RUN_HOURS

    # Objective: maximize total profit
    profit_terms = []
    for hour in range(n_hours):
        gen_mwh = MIN_CAP * is_on[hour] + gen_above_min[hour]

        start_power = (
            start_types[1]["power"] * start_type_1[hour]
            + start_types[2]["power"] * start_type_2[hour]
            + start_types[3]["power"] * start_type_3[hour]
        )
        start_gas = (
            start_types[1]["gas"] * start_type_1[hour]
            + start_types[2]["gas"] * start_type_2[hour]
            + start_types[3]["gas"] * start_type_3[hour]
        )
        start_co2 = (
            start_types[1]["co2"] * start_type_1[hour]
            + start_types[2]["co2"] * start_type_2[hour]
            + start_types[3]["co2"] * start_type_3[hour]
        )

        revenue = power_price[hour] * (gen_mwh + start_power)
        costs = gas_price[hour] * (gas_in_mwh[hour] + start_gas) + co2_price[hour] * (co2_ton[hour] + start_co2)
        profit_terms.append(revenue - costs)

    model += pulp.lpSum(profit_terms)

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=60, gapRel=0.001) # 0.1% of optimal
    print("Solving...")
    model.solve(solver)
    print("Found!")

    # Output the results
    rows = []
    for hour in range(n_hours):
        on_val = int(round(pulp.value(is_on[hour]) or 0))
        start_val = int(round(pulp.value(start[hour]) or 0))

        st1 = int(round(pulp.value(start_type_1[hour]) or 0))
        st2 = int(round(pulp.value(start_type_2[hour]) or 0))
        st3 = int(round(pulp.value(start_type_3[hour]) or 0))
        stype = 1 if st1 == 1 else (2 if st2 == 1 else (3 if st3 == 1 else 0))

        gen_above = float(pulp.value(gen_above_min[hour]) or 0.0)
        gen_total = MIN_CAP * on_val + gen_above

        gas_in = float(pulp.value(gas_in_mwh[hour]) or 0.0)
        co2_use = float(pulp.value(co2_ton[hour]) or 0.0)

        start_power = (start_types[1]["power"] * st1 + start_types[2]["power"] * st2 + start_types[3]["power"] * st3)
        start_gas = (start_types[1]["gas"] * st1 + start_types[2]["gas"] * st2 + start_types[3]["gas"] * st3)
        start_co2 = (start_types[1]["co2"] * st1 + start_types[2]["co2"] * st2 + start_types[3]["co2"] * st3)

        revenue = power_price[hour] * (gen_total + start_power)
        costs = gas_price[hour] * (gas_in + start_gas) + co2_price[hour] * (co2_use + start_co2)
        profit = revenue - costs

        rows.append(
            {
                "hour": hour,
                "power_price": power_price[hour],
                "gas_price": gas_price[hour],
                "co2_price": co2_price[hour],
                "is_on": on_val,
                "start": start_val,
                "start_type": stype,
                "generation_mw": gen_total,
                "startup_power_mwh": float(start_power),
                "gas_input_mwh": gas_in,
                "co2_ton": co2_use,
                "startup_gas_mwh": float(start_gas),
                "startup_co2_ton": float(start_co2),
                "profit": float(profit),
            }
        )

    results = pd.DataFrame(rows)
    results["profit_cum"] = results["profit"].cumsum()

    output_name = f"{out_dir}/results_sim_{num_simulation}.csv"
    results.to_csv(output_name, index=False)
    print(f"Results saved are saved in {output_name}")

    return results


def main():
    file_path = "data/prices.xlsx"
    df = pd.read_excel(file_path, sheet_name=0, skiprows=1)
    df.columns = [x.lower() for x in df.columns]

    for num_simulation in range(1, 6):
        print(f"Processing simulation {num_simulation}...")

        power_price = df[f"power_{num_simulation}"].values
        gas_price = df[f"gas_{num_simulation}"].values
        co2_price = df[f"co2_{num_simulation}"].values

        solve_one_simulation(power_price, gas_price, co2_price, num_simulation, out_dir="data/output")


if __name__ == "__main__":
    main()