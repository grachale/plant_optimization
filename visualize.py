import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

result_files = sorted(glob.glob("data/output/results_sim_*.csv"))

all_results = []

for file_path in result_files:
    print(f"Visualizing results for {file_path}")
    results = pd.read_csv(file_path)

    sim_name = os.path.splitext(os.path.basename(file_path))[0]
    results["datetime"] = pd.date_range(start="2022-01-01 00:00", periods=len(results), freq="H")
    results["simulation"] = sim_name
    all_results.append(results)

    # 1. Plot plant on/off status
    plt.figure(figsize=(15, 3))
    plt.step(results["datetime"], results["is_on"], where="mid", label="Plant On", color="green")
    plt.title(f"Plant On/Off Status ({sim_name})")
    plt.xlabel("Datetime")
    plt.ylabel("On/Off")
    plt.ylim(-0.1, 1.1)
    plt.yticks([0, 1], ["Off", "On"])
    plt.tight_layout()
    plt.savefig(f"data/visualizations/{sim_name}_01_on_off.png", dpi=150)
    plt.close()

    # 2. Plot generation
    plt.figure(figsize=(15, 4))
    plt.plot(results["datetime"], results["generation_mw"], label="Generation (MW)")
    plt.title(f"Generation Profile ({sim_name})")
    plt.xlabel("Datetime")
    plt.ylabel("MW")
    plt.tight_layout()
    plt.savefig(f"data/visualizations/{sim_name}_02_generation.png", dpi=150)
    plt.close()

    # 3. Plot hourly profit
    plt.figure(figsize=(15, 4))
    plt.plot(results["datetime"], results["profit"], label="Hourly Profit")
    plt.axhline(0, linewidth=1)
    plt.title(f"Hourly Profit ({sim_name})")
    plt.xlabel("Datetime")
    plt.ylabel("Profit")
    plt.tight_layout()
    plt.savefig(f"data/visualizations/{sim_name}_03_profit_hourly.png", dpi=150)
    plt.close()

    # 4. Plot cumulative profit
    plt.figure(figsize=(15, 4))
    plt.plot(results["datetime"], results["profit_cum"], label="Cumulative Profit")
    plt.title(f"Cumulative Profit ({sim_name})")
    plt.xlabel("Datetime")
    plt.ylabel("Cumulative Profit")
    plt.tight_layout()
    plt.savefig(f"data/visualizations/{sim_name}_04_profit_cumulative.png", dpi=150)
    plt.close()

    # 5. Plot prices vs generation
    fig, ax1 = plt.subplots(figsize=(15, 4))
    ax1.plot(results["datetime"], results["power_price"], label="Power Price")
    ax1.set_xlabel("Datetime")
    ax1.set_ylabel("Power Price")

    ax2 = ax1.twinx()
    ax2.plot(results["datetime"], results["generation_mw"], label="Generation (MW)")
    ax2.set_ylabel("Generation (MW)")

    plt.title(f"Power Price vs Generation ({sim_name})")
    fig.tight_layout()
    plt.savefig(f"data/visualizations/{sim_name}_05_power_price_vs_generation.png", dpi=150)
    plt.close()

    # 6. Plot starts and start types
    plt.figure(figsize=(15, 3))
    plt.scatter(
        results.loc[results["start"] == 1, "datetime"],
        results.loc[results["start"] == 1, "start_type"],
    )
    plt.title(f"Start Events by Type ({sim_name})")
    plt.xlabel("Datetime")
    plt.ylabel("Start Type")
    plt.yticks([1, 2, 3], ["Type 1 (<=10h off)", "Type 2 (11-35h off)", "Type 3 (>35h off)"])
    plt.tight_layout()
    plt.savefig(f"data/visualizations/{sim_name}_06_start_types.png", dpi=150)
    plt.close()

# 7. Plot comparison of different simulations (cumulative profit)
combined = pd.concat(all_results, ignore_index=True)

plt.figure(figsize=(15, 5))
for sim_name in sorted(combined["simulation"].unique()):
    sim_df = combined[combined["simulation"] == sim_name]
    plt.plot(sim_df["datetime"], sim_df["profit_cum"], label=sim_name)

plt.title("Cumulative Profit Comparison Across Simulations")
plt.xlabel("Datetime")
plt.ylabel("Cumulative Profit")
plt.legend()
plt.tight_layout()
plt.savefig("data/visualizations/all_sims_07_profit_cumulative_comparison.png", dpi=150)
plt.close()

print(f"Done!")
