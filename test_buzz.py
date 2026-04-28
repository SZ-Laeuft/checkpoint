from gpiozero import TonalBuzzer
from time import sleep

tb = TonalBuzzer(18, octaves=4)

print("Sweeping frequencies... listen for the loudest volume.")
            # Three quick rising notes (C5, E5, G5) 
            # High frequency for outdoor piercing power
            for freq in [1046, 1318, 1568]: 
                tb.play(freq)
                sleep(0.08) # Short and punchy
            
            # Hold the last note slightly longer for 'triumph'
            tb.play(2093) # C6 (High C)
            sleep(0.15)
            tb.stop()
tb.stop()