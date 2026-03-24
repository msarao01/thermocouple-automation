from machine import Pin, SPI
import time
from st7796 import ST7796

# ------------------------
# SPI + LCD Setup
# ------------------------
spi = SPI(0, baudrate=5000000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(19), miso=Pin(16))

dc  = Pin(10, Pin.OUT)
rst = Pin(20, Pin.OUT)
cs_lcd = Pin(21, Pin.OUT)

# Backlight
Pin(9, Pin.OUT).value(1)

# Init display
tft = ST7796(spi=spi, width=480, height=320, dc=dc, reset=rst, cs=cs_lcd, rotation=1)
time.sleep_ms(50)

# Colors
WHITE = tft.rgb(255, 255, 255)
BLACK = tft.rgb(0, 0, 0)

# ------------------------
# MAX31855 Thermocouple Setup
# ------------------------
cs1 = Pin(15, Pin.OUT, value=1)
cs2 = Pin(14, Pin.OUT, value=1)
cs3 = Pin(13, Pin.OUT, value=1)
cs4 = Pin(12, Pin.OUT, value=1)
cs5 = Pin(11,  Pin.OUT, value=1)
max_cs = [cs1, cs2, cs3, cs4, cs5]

def read_max31855(cs):
    cs.value(0)
    time.sleep_us(5)
    raw = spi.read(4)
    cs.value(1)

    if not raw:
        return None

    data = int.from_bytes(raw, "big")

    if data & 0x7:  # fault bits
        return None

    temp = (data >> 18) & 0x3FFF
    if temp & 0x2000:  # negative
        temp -= 1 << 14

    return temp * 0.25

# ------------------------
# Layout Setup
# ------------------------
x_label = 20
x_value = 100
y_start = 40
y_step  = 40
box_w   = 200
box_h   = 30

old_values = [None] * 5  # track previous values for partial update

# Draw static labels
tft.fill(BLACK)
for i in range(5):
    tft.upscaled_text(x_label, y_start + i*y_step, f"TC{i+1}:", WHITE, bgcolor=BLACK, scale=2)

# ------------------------
# Partial update function
# ------------------------
def update_cell(i, value):
    y = y_start + i*y_step
    text = "ERR" if value is None else f"{value:.2f}C"

    if old_values[i] != text:
        # erase old value
        tft.fill_rect(x_value, y, box_w, box_h, BLACK)
        # draw new value
        tft.upscaled_text(x_value, y, text, WHITE, bgcolor=BLACK, scale=2)
        old_values[i] = text

# ------------------------
# MAIN LOOP
# ------------------------
while True:
    temps = [read_max31855(cs) for cs in max_cs]

    # Update LCD cells
    for idx in range(5):
        update_cell(idx, temps[idx])

    # Optionally print to console
    print(", ".join(["ERR" if t is None else f"{t:.2f}" for t in temps]))

    time.sleep(1)
