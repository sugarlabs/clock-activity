# Clock activity

## What is this?

The Clock activity is for you to learn how to read time, even if you do not own a watch.

## How to use?

Clock is part of the Sugar desktop.  Please refer to;

* [How to Get Sugar on sugarlabs.org](https://sugarlabs.org/),
* [How to use Sugar](https://help.sugarlabs.org/),
* [How to use Clock](https://help.sugarlabs.org/clock.html)

## License
This activity and its code is put under public domain. Do whatever you want with it!
If you want to contact me: Pierre Métras <pierre@alterna.tv>


## Localization of the Clock
The code for the Clock activity is easily localizable to be used in Sugar with different languages and locales. To achieve that, we tried to put into gettext dictionnary all elements which could be culturally different, such as the fonts used to display texts in the clock. We also used Pango to have a better font management and give the translators the ability to adapt the display of text to their locale.

The Clock uses small messages. As with GUI software, it could be that the same messages have to be used in different contexts, and sometimes localized with different values (depending of the context). For instance, the font used to print the date in the Analog and Digital clock views are the same in the English/USA environment, but the font for the Digital one has to be reduced when using the Indi environment.

GNU gettext tool provides the pgettext() function to deal with such situations (see http://www.gnu.org/software/gettext/manual/gettext.html#Ambiguities). Sadly, the Python binding of gettext does not offer this function. I had to define a custom pgettext() and use it as a workaround, while we wait to have it included in a future Python version.


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

### Translation Wiki
For more information, please visit:
[Translation Wiki](https://github.com/sugarlabs/clock-activity/wiki)


### The color codes to use:
- Hours		blue: `#005FE4`
- Minutes	green: `#00B20D`
- Seconds	red: `#E6000A` (You probably never have to use this one)
- Days		dark red: `#B20008`
- Months	purple: `#5E008C`
- Years		brown: `#9A5200`


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
- [x] Python does not support *pgettext (particular gettext)*. So it makes it difficult to localize identical short strings used in different contexts. clock.py includes a custom function _p(). Better localization support has been added to Python 2.6, in particular pgettext.

- [x] Python 2.5 as used on OLPC XO has a bug with *datetime.strftime(pattern)*, when pattern is longer than around 100 characters. *time.strftime()* does not exhibit that bug and is used as a workaround. Python 2.5.1 seems not to have this bug. http://bugs.python.org/issue2490.
Version 5 of the Clock activity was developped specifically for XO build 8.2.0 which solved this bug. Use version 4 of the Clock with older builds.

- [ ] Whenever the label where the time is displayed becomes wider than the screen width, forinstance when you rotate the display, it would be nice to have line wrapping. I was unable to get it working. The *Label.set_line_wrap(True)* method does not give the expected result.

- [x] The first time the talking clock or the "time in letters" toolbar button ispressed, their is a few seconds latence when Python loads the code. Some can think that these buttons have no action; please wait a few seconds... This effect has been lowered by using threads in GObject library.


## POINT OF INTEREST IN THE CODE
- Developped at 99% on a XO. I was only missing a SVG editor for the icons. But even the icons where hand crafted...

- How to create a new GTK+ widget and paint its content.

- The usage of pango markup to offer better flexibility in localization.

- The signal "notify::active" sent by Sugar to an activity when it comes on the front. In this activity, we stop refreshing the display when we are not active.

- Full pydoc documentation.

- Using the badly documented *gobject.threads_init()* to have better messages processing.


## TODO
A drop box for ideas. While the goal is to keep the source simple and understandable by Python starters, here are listed some ideas of features to include in the Clock activity to help learning how to read the time and have at the same time a usefull clock.

- [ ] An alarm clock mode
- [ ] A stopwatch mode
- [ ] Print the timezone
- [x] A talking clock: speaking the time aloud every minute.(version 5)
- [ ] A Big Ben chime
- [ ] Add a second toolbar to print calendars and to learn how to read the date.
