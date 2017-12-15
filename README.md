﻿# Notes about the Clock activity

## License
This activity and its code is put under public domain. Do whatever you want with it!
If you want to contact me: Pierre Métras <pierre@alterna.tv>


## Localization of the Clock
The code for the Clock activity tries to be easily localizable to be used in Sugar with different languages and locales. To achieve that, we tried to put into gettext dictionnary all elements which could be culturally different, like the fonts used to display texts in the clock. We used also Pango to have a better font management and give the translators the ability to adapt the display of text to their locale.

The Clock uses small messages. As with GUI software, it could be that the same messages have to be used in different contexts, and sometimes localized with different values (depending of the context). For instance, the font used to print the date in the Analog and Digital clock views are the same in the English/USA environment, but the font for the Digital one has to be reduced when using the Indi environment.
GNU gettext tool provides the pgettext() function to deal with such situations (see http://www.gnu.org/software/gettext/manual/gettext.html#Ambiguities). Saddly, the Python binding of gettext does not offer this function. I had to define a custom pgettext() and use it as a workaround, while we wait to have it included in a future Python version.


## Note to translators: how to translate Pango markup?
Usage of Pango markup gives you a great deal of flexibility in the localization of the Clock activity. Let's take an example from the po/fr.po French localization file:
```
#TRANS: datetime.strftime() format
#, no-python-format
msgctxt "Digital Clock"
msgid "<markup><span lang=\"en\" font_desc=\"Sans Bold 80\">%x</span></markup>
msgstr "<markup><span lang=\"fr\" font_desc=\"Sans Bold 70\">%d %B %Y</span></markup>
```
First, I changed the language code from "en" to "fr". Using the right language code let Pango determine the right rules for the layout of the text, for instance from right to left generally for Arabic.

Second, the "%x" format was not correctly supported by the internalization libraries on Build 653: it printed the date as "2008-03-26" instead of "26/03/2008" in French usage. So I decided to use a custom date layout to work around that bug. While at it, I decided that I would display the month name in full letters instead of the number of the month, like "26 mars 2008", with the strftime format "%d %B %Y".

After having changed the date format, I felt that some dates, like "31 octobre 2008" won't display correctly with all display orientations, and I went to reduce the font size from 80 pt to 70 pt. You could also decide to change the font family and use a better font instead of "Sans".

Don't hesitate to adapt the Clock to your local needs...


## How to write the time in full letters for your locale?
The activity use a small inference engine to translate a numeric time to words. This translation is done following rules which have to be localized. I've provided 3 examples, for English, French and Spanish.
This time in full letters is then used by the Text To Speech engine espeak to read aloud the time on demand or when minutes change.

The inference engine tries to find a rule whose pattern is "time(h,m)" where the variable "h" is bound to the current hours and the variable "m" is bound to then current minutes. The rules are scanned in the order they are written, until we find one matching.

For the match to succeed, we can add range conditions with the syntax "[val1 < val2]" or "[val1 < val2 < val3]" after the rule pattern. For instance, if we want to write two rules for hours in the morning and the afternoon, we could write:
```
  time(h, m) [h < 12] => ... 
  time(h, m) [11 < h] => ... |
```
As you can see from the previous example, the conditions of the rules precedes the sign "=>" which specifies the right side of the rules with the actions to execute when the match on the left side succeeds. The rules ends at the "|" character.

On the right side of a rule, after the "=>" sign, you can put a combination of text or other rules calls. The text is used as-is and substituted in the result. If it's a rule call, the inference engine will try again from the start to find a matching rule. For instance:
```
  time(12, 0) => noon |
  time(24, 0) => midnight |
  time(h, 0) => number(h) o'clock |
```
With the first two rules, the engine will display "noon" or "midnight" when called respectively with the values "time(12, 0)" or "time(24, 0)". With the last rule, when called with the pattern "time(h, 0)" where "h" is value different from 12 or 24 (because caught by the two previous rules), the engine will try to find a rule name "number(_)" and when found and matched, will replace the value returned in the text to be concatenated with the text "o'clock".

Inside right side of rules, that is between "=>" and "|", spaces are significative. You can use the operator "#" to concatenate two pieces of text or rules calls, like in:
```
  hour(h) => number(h) hour#plural(h) |
  plural(1) => |
  plural(_) => s |
```
Use "\#" to get the character "#". This is usefull when using pango markup in the text.

As you have probably understod from now, rules patterns or calls use functional syntax: the name of the rule, with arguments between parenthesis. Numerical arguments are considered constants (could be hours or minutes, for example), while alphabetic are variables, bould during the pattern matching or call. The special variable "_" (underscore) is a anonymous variable: its value is not important to the rule firing. For instance, in the previous example, then rule "plural(_) => |" can be read "the plural of anything which is not 1 is 's'".

To test your set of rules, you can create the file 'test_timewriter/LANG_rules.py' where LANG is the ISO code for your language. It's simpler to copy an existing file from the test_timewriter directory and adapt it to your language.
In that file, you just have to declare the '_time_rules' variable containing the source code of your rules. For instances, something like the following:
```python
  #! /usr/bin/env python
  # -*- coding: utf-8 -*-
  _time_rules = """
      time(h, m) => ...
      """
```
Then, you can check your rules with the command:
```	$ python timewriter.py LANG ```
where LANG is the ISO code for your language. It will display all the rules analyzed by the timewriter parser, and then display all times from 0:00 to 23:59.


## Pango markup in the rules
As this activity is aimed at learning how to read the time, we have to offer ways for the children to recognize the important parts of the time expression. The use of a consistent color conventions is part of the job. Hours are displayed in blue, minutes in green, seconds in red as frequently seen in analog clock faces.

This color convention has to be kept, whenever possible, in the time displayed in full letters. The colors have been selected to maximize contrast on the XO. It means that the inference rules used to write the time must include pango markup around the different parts of the time in the sentence, like:

``` 
  time(h, m) [m < 31] => <span foreground="\#00B20D">min(m)</span> past <span foreground="\#005FE4">hour(h)</span> am_pm(h) |
``` 

As this reduce the readability of the rules, I suggest you to write the set of localized rules without the coloring, and later add the pango codes.

#### The color codes to use:
- Hours		blue: `#005FE4`
- Minutes	green: `#00B20D`
- Seconds	red: `#E6000A` (You probably never have to use this one)
- Days		dark red: `#B20008`
- Months	purple: `#5E008C`
- Years		brown: `#9A5200`


## How to debug your localization file?
As you've seen from previous paragraphs, a lot of parameters and logic for the activity is taken from the localization file. It could happen that a change or translation you've done breaks the activity.
To find where the problem lies, it helps to start the Log activity and look at the log file tv.alterna.Clock-N.log. You could find some hints where Python or Sugard breaks when running the activity.
You can also send me an email for assistance, to <pierre@alterna.tv>. Don't forget to attach your locale file and some explanations where it breaks.


## Commands used to generate localized messages files
CAREFULL: _p() Python method is mapped to *pgettext(msgctxt, msgstr)*.

The following procedure has to be done from a XO or a computer using UTF-8 as system encoding.

Clock$ is the prompt when I'm in the Clock directory.

## First run

1. Create the first messages template
    ```
    Clock$ xgettext --output=po/Clock.pot --add-comment --keyword=_p:1c,2 clock.py timewriter.py speaker.py
    ```

2. Adapt po/Clock.pot file with author, copyright, etc.

      ```
      Clock$ vi po/Clock.pot
      ```

3. Initialize a new locale for French

      ```
      Clock$ msginit --input=po/Clock.pot --output-file=po/fr.po --locale=fr
      ```

4. Translate the messages in French

    ```
    Clock$ vi po/fr.po
    ```

5. Create the binary messages file

    ```
    Clock$ msgfmt --output-file=locale/fr/LC_MESSAGES/tv.alterna.Clock.mo --check po/fr.po
    ```

## Messages update
When the sources have changed

1. Extract the new messages from the source like upper, in the po/Clock.pot file.

2. Update a translated message file

    ```
    Clock$ $ msgmerge --update --backup=simple po/fr.po po/Clock.pot
    ```

3. Translate the new messages and generate the binary file.



## BUGS
- SOLVED: Python does not support *pgettext (particular gettext)*. So it makes it difficult to localize identical short strings used in different contexts. clock.py includes a custom function _p(). Better localization support has been added to Python 2.6, in particular pgettext.

- SOLVED: Python 2.5 as used on OLPC XO has a bug with *datetime.strftime(pattern)*, when pattern is longer than around 100 characters. *time.strftime()* does not exhibit that bug and is used as a workaround. Python 2.5.1 seems not to have this bug. http://bugs.python.org/issue2490.
Version 5 of the Clock activity was developped specifically for XO build 8.2.0 which solved this bug. Use version 4 of the Clock with older builds.

- Whenever the label where the time is displayed becomes wider than the screen width, forinstance when you rotate the display, it would be nice to have line wrapping. I was unable to get it working. The *Label.set_line_wrap(True)* method does not give the expected result.

- SOLVED: The first time the talking clock or the "time in letters" toolbar button ispressed, their is a few seconds latence when Python loads the code. Some can think that these buttons have no action; please wait a few seconds... This effect has been lowered by using threads in GObject library.


## POINT OF INTEREST IN THE CODE
- Developped at 99% on a XO. I was only missing a SVG editor for the icons. But even the icons where hand crafted...

- How to create a new GTK+ widget and paint its content.

- The use of pango markup to offer better flexibility in localization.

- The signal "notify::active" sent by Sugar to an activity when it comes on the front. In this activity, we stop refreshing the display when we are not active.

- Full pydoc documentation.

- Using the badly documented *gobject.threads_init()* to have better messages processing.


## TODO
A drop box for ideas. While the goal is to keep the source simple and understandable by Python starters, here are listed some ideas of features to include in the Clock activity to help learning how to read the time and have at the same time a usefull clock.
- An alarm clock mode
- A stopwatch mode
- Print the timezone
- A talking clock: speaking the time aloud every minute. DONE in version 5.
- A Big Ben chime...
- Add a second toolbar to print calendars and to learn how to read the date.