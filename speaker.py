#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Code released in the Public Domain.
# You can do whatever you want with this package.
# Look at NOTES file to see how to adapt this program.
# Originally written by Pierre Métras <pierre@alterna.tv>
# for the OLPC XO laptop.


"""
Speak aloud the text given in the configured language.
"""

from sugar3.speech import SpeechManager


class Speaker:

    """Speak aloud the given text.
    """

    def __init__(self):
        self._speech_manager = SpeechManager()

    def speak(self, text):
        """Speaks aloud the given text.
        """
        text = text.replace("\"", "\\\"")
        if self._speech_manager.enabled():
            self._speech_manager.say_text(text)


if __name__ == "__main__":
    s = Speaker()
    s.speak("It's two o'clock in the morning")
    s.speak("It's seven hours and thirty-four minutes PM")
    # s.speak("Il est quinze heures et vingt-neuf minutes")
    # s.speak("vingt-deux heures dix-huit minutes")
