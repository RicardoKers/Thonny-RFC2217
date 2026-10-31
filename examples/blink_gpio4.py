from machine import Pin
from time import sleep_ms

led = Pin(4, Pin.OUT)

while True:
    led.value(1)
    print("LED LIGADO")
    sleep_ms(500)

    led.value(0)
    print("LED DESLIGADO")
    sleep_ms(500)
