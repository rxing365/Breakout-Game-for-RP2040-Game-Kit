"""
CircuitPython single MP3 playback example for Raspberry Pi Pico.
Plays a single MP3 once.
"""
import board
import audiomp3
import audiopwmio

audio = audiopwmio.PWMAudioOut(board.GP23)

decoder = audiomp3.MP3Decoder(open("pew1_11k_01.mp3", "rb"))
class GameAudio:
    '''Playing sound effects.'''
    def sfx(self, index_number):
        index = 0
        self.index = index_number
        if index == 0:
            audio.play(decoder)
        print("Done playing!")
    