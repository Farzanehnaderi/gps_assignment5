# =======================
#  Farzaneh Naderi 
#  810301115
#  GPS - ASSIGNMENT5
# ======================
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def extract_header_info(filepath):
    """
    Parses the header of a RINEX observation file and returns observation types and index of C1C.
    """
    obs_types = []
    version = None
    with open(filepath, 'r') as file:
        while True:
            line = file.readline()
            if not line:
                raise ValueError("Header ended unexpectedly.")
            if "RINEX VERSION / TYPE" in line:
                version = line[:9].strip()
            elif "SYS / # / OBS TYPES" in line and line.startswith("G"):
                count = int(line[3:6])
                obs_types = line[7:60].split()
                while len(obs_types) < count:
                    next_line = file.readline()
                    obs_types += next_line[7:60].split()
            elif "END OF HEADER" in line:
                break

    if "C1C" not in obs_types:
        raise ValueError("C1C not found in observation types.")

    return {
        "version": version,
        "obs_types": obs_types,
        "c1c_index": obs_types.index("C1C")
    }

def parse_observations(filepath, c1c_index):
    """
    Reads epoch-wise observations and extracts C1C values for GPS satellites only.
    """
    observations = []
    with open(filepath, 'r') as file:
        while True:
            if "END OF HEADER" in file.readline():
                break

        for line in file:
            if not line.startswith(">"):
                continue

            parts = line[1:].split()
            timestamp = datetime.datetime(*map(int, parts[:5]), int(float(parts[5])))
            num_sats = int(parts[7])
            epoch_data = {"time": timestamp, "sat_count": num_sats}

            for _ in range(num_sats):
                obs_line = file.readline()
                if not obs_line.startswith("G"):
                    continue

                prn = obs_line[0:3].strip()
                field_start = 3 + c1c_index * 16
                value_str = obs_line[field_start:field_start + 14].strip()

                if not value_str:
                    continue

                try:
                    value = float(value_str)
                    if value > 0:
                        epoch_data[prn] = value
                except ValueError:
                    continue

            observations.append(epoch_data)

    return observations

def observations_to_dataframe(obs_records):
    """
    Converts list of observations to long-format DataFrame.
    """
    rows = []
    for record in obs_records:
        for sat, val in record.items():
            if sat in ["time", "sat_count"]:
                continue
            rows.append({
                "Time": record["time"],
                "Satellite": sat,
                "C1C_m": val
            })

    return pd.DataFrame(rows)

def save_to_csv(df, filename=None):
    """
    Saves DataFrame with custom columns and sorting to a time-stamped CSV.
    """
    df = df.copy()
    df.insert(0, "Epoch_ID", df.groupby("Time").ngroup() + 1)

    df = df.sort_values(by=["Time", "Satellite"])
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = filename or f"c1c_report_{now}.csv"
    
    df.to_csv(filename, index=False, date_format="%Y-%m-%d %H:%M:%S")
    print(f"\n Custom CSV report saved to: {filename}")


def datetime_to_gps_seconds(dt):
    """
    Converts datetime to GPS seconds-of-week.
    """
    gps_start = datetime.datetime(1980, 1, 6)
    delta = dt - gps_start
    total_sec = delta.total_seconds()
    return total_sec % (7 * 86400)


def plot_pseudorange(df, selected_sats=None):
    """
    Custom-styled plot with annotations and modern design.
    """
    df = df.copy()
    df["GPS_Time_s"] = df["Time"].apply(datetime_to_gps_seconds)

    all_sats = sorted(df["Satellite"].unique())

    if not selected_sats:
        selected_sats = all_sats[:4]
    elif isinstance(selected_sats, int):
        selected_sats = all_sats[:selected_sats]

    pastel_colors = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854']
    markers = ['o', 'v', 's', '^', 'D']

    plt.style.use("seaborn-v0_8-white")
    fig, ax = plt.subplots(figsize=(13, 6))

    for i, sat in enumerate(selected_sats):
        sat_df = df[df["Satellite"] == sat]
        ax.plot(sat_df["Time"], sat_df["C1C_m"],
                label=sat,
                color=pastel_colors[i % len(pastel_colors)],
                marker=markers[i % len(markers)],
                markersize=4,
                linewidth=1.3,
                alpha=0.9)

        if i == 0:
            peak_idx = sat_df["C1C_m"].idxmax()
            peak_time = sat_df.loc[peak_idx, "Time"]
            peak_value = sat_df.loc[peak_idx, "C1C_m"]
            ax.annotate(f'Max {sat}', xy=(peak_time, peak_value),
                        xytext=(peak_time, peak_value + 500),
                        arrowprops=dict(arrowstyle='->', color='gray'),
                        fontsize=9, color='black')

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.set_xlabel("Time (UTC)", fontsize=12)
    ax.set_ylabel("C1C Pseudorange [m]", fontsize=12)
    ax.set_title("Styled Pseudorange Plot with Satellite Annotations", fontsize=14, fontweight='bold')

    ax.grid(True, which='major', linestyle=':', linewidth=0.5, alpha=0.8)
    legend = ax.legend(title="Satellites", loc='upper center', ncol=len(selected_sats),
                       frameon=True, framealpha=0.95, fancybox=True, shadow=False)
    legend.get_frame().set_linewidth(0.3)

    plt.tight_layout()
    plt.show()

# === MAIN PROGRAM === 
if __name__ == "__main__":
    rinex_path = "36.24O"

    print("Reading RINEX Header...")
    header_info = extract_header_info(rinex_path)
    print(f"RINEX Version: {header_info['version']}")
    print(f"Observation Types: {header_info['obs_types']}")
    print(f"C1C index: {header_info['c1c_index']}")

    print("\nParsing observation epochs...")
    obs_data = parse_observations(rinex_path, header_info['c1c_index'])

    print("Transforming to DataFrame...")
    df_obs = observations_to_dataframe(obs_data)

    print("Saving to CSV...")
    save_to_csv(df_obs)

    print("Available Satellites: ")
    print(df_obs["Satellite"].unique())
    user_input = input("Enter satellite PRNs (comma-separated like G01,G02) or a number of satellites to plot: ")
    if user_input.strip().isdigit():
        plot_pseudorange(df_obs, int(user_input.strip()))
    else:
        prns = [s.strip().upper() for s in user_input.split(",") if s.strip()]
        plot_pseudorange(df_obs, prns if prns else None)
