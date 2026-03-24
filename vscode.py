import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import collections
import time
import math
import numpy as np
import csv
from datetime import datetime

SERIAL_PORT = 'COM4'
BAUD_RATE = 115200

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

WINDOW_DURATION = 15 * 60
NUM_TC = 5

# --- CSV LOGGING SETUP ---
timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"thermocouple_log_{timestamp_str}.csv"
csv_file = open(filename, "w", newline="")
csv_writer = csv.writer(csv_file)

csv_writer.writerow(["timestamp"] + [f"TC{i+1}" for i in range(NUM_TC)])

# --- Figure Layout ---
fig = plt.figure(figsize=(12, 6))

ax = fig.add_axes([0.08, 0.1, 0.70, 0.8])
ax.set_title("Live 5-Channel Thermocouple Plot (15-min Window)")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Temperature (°C)")
ax.grid(True, alpha=0.3)

ax_side = fig.add_axes([0.80, 0.1, 0.18, 0.8])
ax_side.axis("off")

# Plot lines
colors = plt.cm.tab20(np.linspace(0, 1, NUM_TC))
lines = []
for i in range(NUM_TC):
    line, = ax.plot([], [], label=f"TC{i+1}", color=colors[i])
    lines.append(line)

ax.legend(ncol=2, fontsize=8)

# Data buffers
x_data = collections.deque()
y_data = [collections.deque() for _ in range(NUM_TC)]

start_time = time.time()

# --- Axis smoothing variables ---
ymin_smooth = None
ymax_smooth = None
SMOOTHING = 0.1


def update(frame):
    global ymin_smooth, ymax_smooth

    raw = ser.readline().decode().strip()

    if not raw:
        return lines

    parts = raw.split(",")

    if len(parts) != NUM_TC:
        return lines

    elapsed = time.time() - start_time
    x_data.append(elapsed)

    faulty = []
    parsed_values = []

    # --- Parse thermocouple values ---
    for i, text in enumerate(parts):
        try:
            if text.strip().lower() == "none" or text.strip() == "":
                raise ValueError

            val = float(text)

            # Filter unrealistic spikes
            if val < -50 or val > 1000:
                raise ValueError

        except:
            val = float("nan")
            faulty.append(i + 1)

        parsed_values.append(val)
        y_data[i].append(val)

    # --- WRITE TO CSV ---
    csv_writer.writerow([time.time()] + parsed_values)

    # --- Remove old data ---
    while x_data and elapsed - x_data[0] > WINDOW_DURATION:
        x_data.popleft()
        for buf in y_data:
            buf.popleft()

    # --- Update plot lines ---
    for i in range(NUM_TC):
        lines[i].set_data(x_data, y_data[i])

    ax.set_xlim(max(0, elapsed - WINDOW_DURATION), elapsed)

    # --- Dynamic Y-axis scaling with smoothing ---
    valid_vals = []

    for buf in y_data:
        for v in buf:
            if not math.isnan(v):
                valid_vals.append(v)

    if valid_vals:
        ymin = min(valid_vals)
        ymax = max(valid_vals)

        margin = max(0.5, (ymax - ymin) * 0.15)

        ymin_target = ymin - margin
        ymax_target = ymax + margin

        if ymin_smooth is None:
            ymin_smooth = ymin_target
            ymax_smooth = ymax_target

        ymin_smooth += SMOOTHING * (ymin_target - ymin_smooth)
        ymax_smooth += SMOOTHING * (ymax_target - ymax_smooth)

        ax.set_ylim(ymin_smooth, ymax_smooth)

    # --- Sidebar update ---
    ax_side.clear()
    ax_side.axis("off")

    if faulty:
        ax_side.text(
            0.5, 0.5,
            "FAULTY CHANNELS:\n" + ", ".join([f"TC{i}" for i in faulty]),
            ha="center", va="center",
            fontsize=12, color="red", wrap=True
        )
    else:
        ax_side.text(
            0.5, 0.5,
            "Status:\nAll thermocouples OK",
            ha="center", va="center",
            fontsize=12, color="green", wrap=True
        )

    return lines


ani = FuncAnimation(fig, update, interval=100)

plt.show()

csv_file.close()
