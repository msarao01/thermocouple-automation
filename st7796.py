# Fixed ST7796 driver for MicroPython (SPI mode)
# Works on Raspberry Pi Pico with 480x320 TFT modules

import time
from machine import Pin, SPI
import framebuf

FONT = framebuf.FrameBuffer(bytearray(8*8), 8, 8, framebuf.MONO_HLSB)

class ST7796:
    def __init__(self, spi, width, height, dc, reset, cs, rotation=0):
        self.spi = spi
        self.width = width
        self.height = height
        self.dc = dc
        self.reset = reset
        self.cs = cs
        self.rotation = rotation

        self.cs.off()
        self.reset.off()
        time.sleep_ms(20)
        self.reset.on()
        time.sleep_ms(150)

        self.init_lcd()

    def write_cmd(self, cmd):
        self.dc.off()
        self.spi.write(bytes([cmd]))

    def write_data(self, data):
        self.dc.on()
        self.spi.write(bytes([data]))

    def init_lcd(self):
        self.write_cmd(0x01)
        time.sleep_ms(150)

        self.write_cmd(0x11)
        time.sleep_ms(150)

        self.write_cmd(0x3A)
        self.write_data(0x55)  # 16-bit

        # Proper MADCTL for ST7796
        self.write_cmd(0x36)
        if self.rotation == 0:
            self.write_data(0x48)   # MX + BGR
        elif self.rotation == 1:
            self.write_data(0x28)   # MV + BGR
        elif self.rotation == 2:
            self.write_data(0x88)
        else:
            self.write_data(0xE8)

        self.write_cmd(0x21)  # Inversion ON

        self.write_cmd(0x29)  # Display ON
        time.sleep_ms(100)

    def set_window(self, x0, y0, x1, y1):
        self.write_cmd(0x2A)
        self.dc.on()
        self.spi.write(bytes([
            x0 >> 8, x0 & 0xFF,
            x1 >> 8, x1 & 0xFF
        ]))

        self.write_cmd(0x2B)
        self.dc.on()
        self.spi.write(bytes([
            y0 >> 8, y0 & 0xFF,
            y1 >> 8, y1 & 0xFF
        ]))

        self.write_cmd(0x2C)

    def fill(self, color):
        self.set_window(0, 0, self.width-1, self.height-1)

        hi = (color >> 8) & 0xFF
        lo = color & 0xFF
        line = bytes([hi, lo]) * self.width  # THIS is valid

        self.dc.on()
        for _ in range(self.height):
            self.spi.write(line)
            
    def draw_char(self, x, y, char, color, bgcolor = None, scale =1):
        fb = framebuf.FrameBuffer(bytearray(8), 8, 8, framebuf.MONO_HLSB)
        fb.fill(0)
        fb.text(char, 0, 0, 1)
        
        for py in range(8):
            for px in range(8):
                pixel = fb.pixel(px, py)
                if pixel:
                    if scale > 1:
                        self.fill_rect(x+px*scale, y+py*scale, scale, scale, color)
                    else:
                        self.fill_rect(x+px, y+py*scale, 1, 1, color)
                elif bgcolor is not None:
                    if scale>1:
                        self.fill_rect(x+px*scale, y+py*scale, scale,scale, bgcolor)
                    else:
                        self.fill_rect(x+px, y+py,1,1,bgcolor)
                        
    def fill_rect(self,x,y,w,h,color):
        self.set_window(x, y, x+w-1, y+h-1)
        hi = (color >> 8) & 0xFF
        lo = color & 0xFF
        line = bytes([hi, lo]) * w
        self.dc.on()
        for _ in range(h):
            self.spi.write(line)
                    
    def upscaled_text(self, x, y, text, color, bgcolor=None, scale=2):
        for i, c in enumerate(text):
            self.draw_char(x + i*8*scale, y, c, color, bgcolor, scale)

    def rgb(self, r, g, b):
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

