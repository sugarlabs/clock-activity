#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Code released in the Public Domain. You can do whatever you want
# with this package.  Though I'm learning Python, I've tried to use
# the best practices in XO development.  Look at NOTES file to see how
# to adapt this program.  Originally written by Pierre Métras
# <pierre@alterna.tv> for the OLPC XO laptop.


"""Learning time.
==============
Sugar was missing a simple clock for kids to learn how to
read time, but more importantly to know what time is is. When you
don't own a clock, Sugar can be used to display the time to
arrive in time at school...
A clock can also be used to learn how to count and read numbers.

Display and behavior can be changed with the buttons in the toolbar:
- A simple clock with hours figures to learn to tell the time.
- A nice clock face, without hours numbers.
- A digital clock with a time scale.
Also, the clock can print the current time in full letters. Or speak
it aloud.

To help learning the time, all the clocks displays use a consistent
color code:
- Hours         blue: #005FE4
- Minutes       green: #00B20D
- Seconds       red: #E6000A
- Days          dark red: #B20008
- Months        purple: #5E008C
- Years         brown: #9A5200


An analog clock is also very helpfull to determine where the North is when you
don't have a compass!
Check http://www.wikihow.com/Find-True-North-Without-a-Compass
And knowing where the True North is, you can build a Sun Clock!

Author: Pierre Metras <pierre@alterna.tv>
Based on work from Davyd Madeley, Lawrence Oluyede <l.oluyede@gmail.com>
SVG background adapted from Open ClipArt:
http://openclipart.org/people/rihard/rihard_Clock_Calendar_2.svg

More about clocks and time in the World
---------------------------------------
- Clock face: http://en.wikipedia.org/wiki/Clock_face
- 12 hours clock: http://en.wikipedia.org/wiki/12-hour_clock
- 24 hours clock: http://en.wikipedia.org/wiki/24-hour_clock
- Thai 6 hours clock: http://en.wikipedia.org/wiki/Thai_six-hour_clock

- Time and date in the World:
  http://en.wikipedia.org/wiki/Date_and_time_notation_by_country

"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Rsvg', '2.0')
gi.require_version('PangoCairo', '1.0')
gi.require_version('Gst', '1.0')

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Rsvg
from gi.repository import Pango
from gi.repository import GObject
from gi.repository import PangoCairo
from gi.repository import Gst

import logging
import os
import re
import math
import cairo
import subprocess
from datetime import datetime

from gettext import gettext as _

from sugar3.graphics import style
from sugar3.activity import activity
from sugar3.activity.widgets import StopButton
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.graphics.radiotoolbutton import RadioToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton

from progresstoolbutton import ProgressToolButton
from speaker import Speaker

import dbus

# The display modes of the clock
_MODE_SIMPLE_CLOCK = 0
_MODE_NICE_CLOCK = 1
_MODE_DIGITAL_CLOCK = 2

# directory exists if powerd is running.  create a file here,
# named after our pid, to inhibit suspend.
POWERD_INHIBIT_DIR = '/var/run/powerd-inhibit-suspend'

# Tolerance for grabbing hands, in radians.  Each hand can be grabbed
# if the user press on a piece of the circle that is the angle of the
# hand +- the tolerance angle.
_ANGLE_TOLERANCE = 0.3


Gst.init(None)


class ClockActivity(activity.Activity):

    """The clock activity displays a simple clock widget.
    """

    def __init__(self, handle):
        """Create and initialize the clock activity.
        """
        super(ClockActivity, self).__init__(handle)

        # TRANS: Title of the activity
        self.set_title(_('What Time Is It?'))

        # TRANS: The format used when writing the time in full
        # letters.  You must take care to use a font size large enough
        # so that kids can read it easily, but also small enough so
        # that all times combination fit on the screen, even when the
        # screen is rotated.  Pango markup:
        # http://www.pygtk.org/docs/pygtk/pango-markup-language.html
        self._TIME_LETTERS_FORMAT = _('<markup>\
<span lang="en" font_desc="Sans 20">%s</span></markup>')

        # TRANS: The format used to display the weekday and date
        # (example: Tuesday 10/21/2008) We recommend to use the same
        # font size as for the time display.  See
        # http://docs.python.org/lib/module-time.html for available
        # strftime formats.  xgettext:no-python-format
        self._DATE_SHORT_FORMAT = _('<markup>\
<span lang="en" font_desc="Sans 20">\
<span foreground="#B20008">%A</span>, \
<span foreground="#5E008C">%m</span>/\
<span foreground="#B20008">%d</span>/\
<span foreground="#9A5200">%Y</span></span></markup>')

        # Should we write the time in full letters?
        self._time_in_letters = self.get_title()
        self._time_letters = None
        self._date = None
        self._time_speaker = None

        self._write_time = False
        self._speak_time = False
        self._write_date = False
        self._display_mode_buttons = []

        self._ntp_process = None

        self._make_display()
        self._make_toolbars()

        # Show the activity on the screen
        self.show_all()

        # We want to be notified when the minutes change
        self._clock.connect("time_minute", self._minutes_changed_cb)

        if not self.powerd_running():
            try:
                bus = dbus.SystemBus()
                proxy = bus.get_object('org.freedesktop.ohm',
                                       '/org/freedesktop/ohm/Keystore')
                self.ohm_keystore = dbus.Interface(
                    proxy, 'org.freedesktop.ohm.Keystore')
            except dbus.DBusException:
                self.ohm_keystore = None

        self.connect('notify::active', self._notify_active_cb)

        # Some hardware cannot keep two GStreamer playback pipelines active
        try:
            model = file('/proc/device-tree/openprom/model', 'r').readline()
        except:
            model = 'unknown'

        self._pathetic = False
        if 'CL1   Q2' in model:  # OLPC XO-1
            self._pathetic = True
        if 'CL2   Q4' in model:  # OLPC XO-1.75
            self._pathetic = True

    def write_file(self, file_path):
        self.metadata['write-time'] = str(self._write_time)
        self.metadata['write-date'] = str(self._write_date)
        self.metadata['speak-time'] = str(self._speak_time)
        self.metadata['clock-mode'] = str(self._clock._mode)
        self.metadata['ticking'] = str(self._clock.ticking)
        logging.debug('Saving metadata %s', (self.metadata['write-time'],
                                             self.metadata['write-date'],
                                             self.metadata['speak-time'],
                                             self.metadata['clock-mode'],
                                             self.metadata['ticking']))
        # Need write a empty file or the read_file is not called
        with open(file_path, 'w') as data:
            data.write('')

    def read_file(self, file_path):
        logging.debug('Reading metadata %s', (self.metadata['write-time'],
                                              self.metadata['write-date'],
                                              self.metadata['speak-time'],
                                              self.metadata['clock-mode'],
                                              self.metadata['ticking']))
        if 'clock-mode' not in self.metadata.keys():
            display_mode = _MODE_SIMPLE_CLOCK
        else:
            display_mode = int(self.metadata['clock-mode'])

        if 'write-time' in self.metadata.keys():
            self._write_time = str(self.metadata['write-time']) == 'True'

        if 'speak-time' in self.metadata.keys():
            self._speak_time = str(self.metadata['speak-time']) == 'True'

        if 'write-date' in self.metadata.keys():
            self._write_date = str(self.metadata['write-date']) == 'True'

        if 'ticking' in self.metadata.keys():
            self._clock.ticking = str(self.metadata['ticking']) == 'True'

        logging.debug('Read values %s', (self._write_time,
                                         self._speak_time, self._write_date,
                                         display_mode, self._clock.ticking))

        # apply the changes in the UI
        self._display_mode_buttons[display_mode].set_active(True)
        self._write_time_btn.set_active(self._write_time)
        self._write_date_btn.set_active(self._write_date)
        self._speak_time_btn.set_active(self._speak_time)
        self._ticking_btn.set_active(self._clock.ticking)

    def powerd_running(self):
        self.using_powerd = os.access(POWERD_INHIBIT_DIR, os.W_OK)
        return self.using_powerd

    def _inhibit_suspend(self):
        if self.using_powerd:
            fd = open(POWERD_INHIBIT_DIR + "/%u" % os.getpid(), 'w')
            fd.close()
            return True

        if self.ohm_keystore is not None:
            try:
                self.ohm_keystore.SetKey('suspend.inhibit', 1)
                return self.ohm_keystore.GetKey('suspend.inhibit')
            except dbus.exceptions.DBusException:
                return False
        else:
            return False

    def _allow_suspend(self):
        if self.using_powerd:
            os.unlink(POWERD_INHIBIT_DIR + "/%u" % os.getpid())
            return True

        if self.ohm_keystore is not None:
            try:
                self.ohm_keystore.SetKey('suspend.inhibit', 0)
                return self.ohm_keystore.GetKey('suspend.inhibit')
            except dbus.exceptions.DBusException:
                return False
        else:
            return False

    def _make_toolbars(self):
        """Prepare and set the toolbars of the activity.

        Load and show icons. Associate them to the call back methods.
        """
        self.max_participants = 1
        toolbar_box = ToolbarBox()
        activity_button = ActivityToolbarButton(self)
        activity_button.show()
        toolbar_box.toolbar.insert(activity_button, 0)

        self._add_clock_controls(toolbar_box.toolbar)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_size_request(0, -1)
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.connect('clicked', self._stop_clicked_cb)

        self.set_toolbar_box(toolbar_box)
        toolbar_box.show_all()
        return toolbar_box

    def _add_clock_controls(self, display_toolbar):

        # First group of radio button to select the type of clock to display
        button1 = RadioToolButton(icon_name="simple-clock")
        button1.set_tooltip(_('Simple Clock'))
        button1.connect("toggled", self._display_mode_changed_cb,
                        _MODE_SIMPLE_CLOCK)
        display_toolbar.insert(button1, -1)
        self._display_mode_buttons.append(button1)
        button2 = RadioToolButton(icon_name="nice-clock",
                                  group=button1)
        button2.set_tooltip(_('Nice Clock'))
        button2.connect("toggled", self._display_mode_changed_cb,
                        _MODE_NICE_CLOCK)
        display_toolbar.insert(button2, -1)
        self._display_mode_buttons.append(button2)
        button3 = RadioToolButton(icon_name="digital-clock",
                                  group=button1)
        button3.set_tooltip(_('Digital Clock'))
        button3.connect("toggled", self._display_mode_changed_cb,
                        _MODE_DIGITAL_CLOCK)
        display_toolbar.insert(button3, -1)
        self._display_mode_buttons.append(button3)

        # A separator between the two groups of buttons
        self._add_separator(display_toolbar)

        # Now the options buttons to display other elements: date, day
        # of week...  A button in the toolbar to write the time in
        # full letters
        self._write_time_btn = ToggleToolButton("write-time")
        self._write_time_btn.set_tooltip(_('Display time in full letters'))
        self._write_time_btn.connect("toggled", self._write_time_clicked_cb)
        display_toolbar.insert(self._write_time_btn, -1)

        # The button to display the weekday and date
        self._write_date_btn = ToggleToolButton("write-date")
        self._write_date_btn.set_tooltip(_('Display weekday and date'))
        self._write_date_btn.connect("toggled", self._write_date_clicked_cb)
        display_toolbar.insert(self._write_date_btn, -1)

        # Another button to speak aloud the time
        self._speak_time_btn = ToggleToolButton("microphone")
        self._speak_time_btn.set_tooltip(_('Talking clock'))
        self._speak_time_btn.connect("toggled", self._speak_time_clicked_cb)
        display_toolbar.insert(self._speak_time_btn, -1)

        # Another button to toggle tick
        self._ticking_btn = ToggleToolButton("ticking")
        self._ticking_btn.set_tooltip(_('Ticking clock'))
        self._ticking_btn.connect("toggled", self._ticking_toggled_cb)
        display_toolbar.insert(self._ticking_btn, -1)

        # A separator between the two groups of buttons
        self._add_separator(display_toolbar)

        # And another button to toggle grabbing the hands
        self._grab_button = ToggleToolButton("grab")
        self._grab_button.set_tooltip(_('Grab the hands'))
        self._grab_button.connect("toggled", self._grab_clicked_cb)
        display_toolbar.insert(self._grab_button, -1)

        if os.access('/boot/olpc_build', os.R_OK) and \
           os.access('/usr/sbin/ntpdate', os.R_OK):

            self._add_separator(display_toolbar)

            self._ntp_button = ProgressToolButton(icon_name="emblem-downloads")
            self._ntp_button.set_tooltip(_('Download time'))
            self._ntp_button.connect("clicked", self._ntp_clicked_cb)
            self._ntp_button.update(0.05)
            display_toolbar.insert(self._ntp_button, -1)

    def _add_separator(self, display_toolbar):
        separator = Gtk.SeparatorToolItem()
        separator.set_draw(True)
        display_toolbar.insert(separator, -1)

    def _make_display(self):
        """Prepare the display of the clock.

        The display has two parts: the clock face at the top, and the
        time in full letters at the bottom, when the user selects to
        show it.
        """
        # The clock face
        self._clock = ClockFace()

        # The label to print the time in full letters
        self._time_letters = Gtk.Label()
        self._time_letters.set_no_show_all(True)
        # Following line in ineffective!
        # self._time_letters.set_line_wrap(True)
        # Resize the invisible label so that Gtk will know in advance
        # the height when we show it.
        self._time_letters.set_markup(
            self._TIME_LETTERS_FORMAT % self._time_in_letters)

        # The label to write the date
        self._date = Gtk.Label()
        self._date.set_no_show_all(True)
        self._date.set_markup(
            self._clock.get_time().strftime(self._DATE_SHORT_FORMAT))

        # Put all these widgets in a vertical box
        vbox = Gtk.VBox()
        vbox.pack_start(self._clock, True, True, 0)
        vbox.pack_start(self._time_letters, False, False, 0)
        vbox.pack_start(self._date, False, False, 0)

        # Attach the display to the activity
        self.set_canvas(vbox)
        self._clock.active = True

    def _write_date_clicked_cb(self, button):
        """The user clicked on the "write date" button to display the
        current weekday and date.
        """
        self._write_date = button.get_active()
        if button.get_active():
            self._date.show()
        else:
            self._date.hide()

    def _display_mode_changed_cb(self, radiobutton, display_mode):
        """The user selected a clock display mode (simple clock, nice
        or digital).
        """
        self._clock.set_display_mode(display_mode)
        self._clock.queue_draw()

        is_digital = display_mode == _MODE_DIGITAL_CLOCK

        # Exit grab hands mode if the clock is digital
        if self._clock.grab_hands_mode and is_digital:
            self._grab_button.set_active(False)

        # The hands can't be grabbed in the digital clock mode
        self._grab_button.props.sensitive = not is_digital

    def _write_time_clicked_cb(self, button):
        """The user clicked on the "write time" button to print the
        current time.
        """
        self._write_time = button.get_active()
        if self._write_time:
            self._time_letters.show()
            self._write_and_speak(False)
        else:
            self._time_letters.hide()

    def _speak_time_clicked_cb(self, button):
        """The user clicked on the "speak time" button to hear the
        talking clock.
        """
        self._speak_time = button.get_active()
        if self._pathetic:
            self._ticking_btn.set_sensitive(not self._speak_time)
        self._write_and_speak(self._speak_time)

    def _ticking_toggled_cb(self, button):
        """The user clicked on the "ticking clock" button to hear or
        not hear the clock ticking.  """
        self._clock.ticking = button.get_active()
        if self._pathetic:
            self._speak_time_btn.set_sensitive(not self._clock.ticking)

    def _grab_clicked_cb(self, button):
        """The user clicked on the "grab hands" button to toggle
        grabbing the hands.
        """
        self._clock.change_grab_hands_mode(button.get_active())

    def _minutes_changed_cb(self, clock):
        """Minutes have changed on the clock face: we have to update
        the display of the time in full letters if the user has chosen
        to have it and eventually croak the time.
        """
        # Change time display and talk, if necessary
        self._write_and_speak(True)

        # Update the weekday and date in case it was midnight
        self._date.set_markup(
            clock.get_time().strftime(self._DATE_SHORT_FORMAT))

    def _notify_active_cb(self, widget, pspec):
        """Sugar notify us that the activity is becoming active or
        inactive.

        When we are inactive, we change the activity status of the
        clock face widget, so that it can stop updating every seconds.
        """
        self._clock.active = self.props.active
        if self.props.active:
            self._inhibit_suspend()
        else:
            self._allow_suspend()

    def _write_and_speak(self, speak):
        # Only update the time in full letters when necessary
        if self._write_time or self._speak_time:
            self._do_write_time()

        # And if requested, say it aloud
        if self._speak_time and speak:
            GObject.idle_add(self._do_speak_time)

    def _do_write_time(self):
        """Translate the time to full letters.
        """
        hour = self._clock.get_time().hour
        minute = self._clock.get_time().minute

        # TRANS: Hour, referring to the unit of time. This list
        # iterates through each unit of the 12-hour clock twice in
        # word form so one AM would have the same translation as one PM.
        hours = [_('twelve'), _('one'), _('two'), _('three'), _('four'),
                 _('five'), _('six'), _('seven'), _('eight'), _('nine'),
                 _('ten'), _('eleven'), _('twelve'), _('one'), _('two'),
                 _('three'), _('four'), _('five'), _('six'), _('seven'),
                 _('eight'), _('nine'), _('ten'), _('eleven')]

        # TRANS: Minute, referring to the unit of time. This list
        # iterates through 60 minutes in word form.
        minutes = [_('one'), _('two'), _('three'), _('four'), _('five'),
                   _('six'), _('seven'), _('eight'), _('nine'), _('ten'),
                   _('eleven'), _('twelve'), _('thirteen'), _('fourteen'),
                   _('fifteen'), _('sixteen'), _('seventeen'), _('eighteen'),
                   _('nineteen'), _('twenty'), _('twenty-one'),
                   _('twenty-two'), _('twenty-three'), _('twenty-four'),
                   _('twenty-five'), _('twenty-six'), _('twenty-seven'),
                   _('twenty-eight'), _('twenty-nine'), _('thirty'),
                   _('thirty-one'), _('thirty-two'), _('thirty-three'),
                   _('thirty-four'), _('thirty-five'), _('thirty-six'),
                   _('thirty-seven'), _('thirty-eight'), _('thirty-nine'),
                   _('forty'), _('forty-one'), _('forty-two'),
                   _('forty-three'), _('forty-four'), _('forty-five'),
                   _('forty-six'), _('forty-seven'), _('forty-eight'),
                   _('forty-nine'), _('fifty'), _('fifty-one'),
                   _('fifty-two'), _('fifty-three'), _('fifty-four'),
                   _('fifty-five'), _('fifty-six'), _('fifty-seven'),
                   _('fifty-eight'), _('fifty-nine'), _('sixty')]

        # TRANS: "o clock", used after a number from one to twelve to
        # indicate the hour of the day or night, eg. "one o clock PM"
        oClock = _('o clock')

        # TRANS: AM or PM, referring to morning (before 12PM) or
        # afternoon (12PM and after).
        period = [_('AM'), _('PM')]

        if hour < 12:
            periodHour = 0
        else:
            periodHour = 1

        if hour == 12 and minute == 0:
            # TRANS: "Noon", as in afternoon 12PM
            self._time_in_letters = (
                '<markup><span lang="en" font_desc="Sans 20">' +
                '<span foreground="#005FE4">' + _('noon') +
                '</span></span></markup>')
        elif hour == 0 and minute == 0:
            # TRANS: "Midnight", as in morning 12AM
            self._time_in_letters = (
                '<markup><span lang="en" font_desc="Sans 20">' +
                '<span foreground="#005FE4">' +
                _('midnight') + '</span></span></markup>')
        elif minute == 0:
            # TRANS: Use "hour o clock period" when minute == 0,
            # eg. "one o clock PM"
            self._time_in_letters = (
                '<markup><span lang="en" font_desc="Sans 20">' +
                _('<span foreground="#005FE4">%(hour)s</span>' +
                  '<span foreground="#00B20D"> %(minute)s</span>' +
                  '<span foreground="#B20008"> %(period)s</span>') +
                '</span></markup>') % {'hour': hours[hour],
                                       'minute': oClock,
                                       'period': period[periodHour]}
        else:
            # TRANS: This takes on the format of "hour minute period",
            # eg. "one forty AM"
            self._time_in_letters = (
                '<markup><span lang="en" font_desc="Sans 20">' +
                _('<span foreground="#005FE4">%(hour)s</span>' +
                  '<span foreground="#00B20D"> %(minute)s</span>' +
                  '<span foreground="#B20008"> %(period)s</span>') +
                '</span></markup>') % {'hour': hours[hour],
                                       'minute': minutes[minute - 1],
                                       'period': period[periodHour]}

        self._time_letters.set_markup(
            self._TIME_LETTERS_FORMAT % self._time_in_letters)

    def _do_speak_time(self):
        """Speak aloud the current time.
        """
        if self._time_speaker is None:
            self._time_speaker = Speaker()
        self._time_speaker.speak(self._untag(self._time_in_letters))

    def _untag(self, text):
        """Remove all the tags (pango markup) from a text.
        """
        if text is False or "<" not in text:
            return text
        else:
            result = ""
            for s in re.findall(r"(<.*?>)|([^<>]+)", text):
                result += s[1]
            return result

    def _ntp_clicked_cb(self, button):
        if self._ntp_process:
            return

        args = ["su", "-c", "/usr/sbin/ntpdate -u pool.ntp.org"]
        self._ntp_process = subprocess.Popen(args, bufsize=-1,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
        self._ntp_counter = 0

        GObject.timeout_add(100, self._ntpdate_poll_cb)

        button.update(0.1)
        button.set_tooltip(_('Download time began'))

    def _ntpdate_poll_cb(self):
        if self._ntp_process.poll() is None:
            self._ntp_counter += 1
            self._ntp_button.update(0.1 + (self._ntp_counter / 90.0))
            return True

        if self._ntp_process.returncode:
            data = self._ntp_process.communicate()
            logging.error('Download time failed (%d), %r',
                          self._ntp_process.returncode,
                          repr(data))

            self._ntp_button.update(0.05)
            self._ntp_button.set_tooltip(_('Download time failed (%d)') %
                                         self._ntp_process.returncode)
            return False

        args = ["su", "-c", "/usr/sbin/hwclock --systohc"]
        self._ntp_process = subprocess.Popen(args, bufsize=-1,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)

        self._ntp_counter = 0
        GObject.timeout_add(100, self._hwclock_poll_cb)
        return False

    def _hwclock_poll_cb(self):
        if self._ntp_process.poll() is None:
            self._ntp_counter += 1
            self._ntp_button.update(0.1 + (self._ntp_counter / 20.0))
            self._ntp_button.set_tooltip(_('Setting time in progress'))
            return True

        if self._ntp_process.returncode:
            data = self._ntp_process.communicate()
            logging.error('Setting time failed (%d), %r',
                          self._ntp_process.returncode,
                          repr(data))

        self._ntp_button.update(1.0)
        self._ntp_button.set_tooltip(_('Download time done'))

        GObject.timeout_add(1000, self._ntp_disable_cb)
        return False

    def _ntp_disable_cb(self):
        self._ntp_button.update(0.0)
        self._ntp_button.set_sensitive(False)
        return False

    def _stop_clicked_cb(self, button):
        self._clock.active = False


class ClockFace(Gtk.DrawingArea):

    """The Pango widget of the clock.

    This widget draws a simple analog clock, with 3 hands (hours,
    minutes and seconds) or a digital clock. Depending on the display
    mode, different information is displayed.
    """

    def __init__(self):
        """Initialize the clock widget.

        The mode defaults to the basic analog clock, with no hours
        mark or date.
        """
        super(ClockFace, self).__init__()

        # Set to True when the variables to draw the clock are set:
        self.initialized = False
        self._simple_background_cache = None
        self._nice_background_cache = None

        # The time on the clock face
        self._time = datetime.now()
        self._old_minute = self._time.minute

        # Update the clock only when the widget is active to save
        # resource
        self._active = False
        self._ticking = False
        self._update_id = None

        # The display mode of the clock
        self._mode = _MODE_SIMPLE_CLOCK

        # Cache for the simple clock face background
        self._simple_background_cache = None

        # SVG Background handle
        self._svg_handle = None

        # This are calculated on widget resize
        self._center_x = 0
        self._center_y = 0
        self._radius = -1
        self._line_width = 2
        self._hand_sizes = {}
        self._hand_angles = {}

        # Color codes (approved colors for Sugar)

        # Medium Blue
        self._COLOR_HOURS = "#005FE4"

        # Medium Green
        self._COLOR_MINUTES = "#00B20D"

        # Medium Red
        self._COLOR_SECONDS = "#E6000A"

        # White
        self._COLOR_WHITE = "#FFFFFF"

        # Black
        self._COLOR_BLACK = "#000000"

        # Gtk.Widget signals
        self.connect("draw", self._draw_cb)
        self.connect("size-allocate", self._size_allocate_cb)

        # The masks to capture the events we are interested in
        self.add_events(Gdk.EventMask.EXPOSURE_MASK |
                        Gdk.EventMask.VISIBILITY_NOTIFY_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.BUTTON1_MOTION_MASK)

        # Define a new signal to notify the application when minutes
        # change.  If the user wants to display the time in full
        # letters, the method of the activity will be called back to
        # refresh the display.
        GObject.signal_new("time_minute", ClockFace,
                           GObject.SIGNAL_RUN_LAST,
                           GObject.TYPE_NONE, [])

        # This flag is True if the clock is in grab hands mode
        self.grab_hands_mode = False

        # When grabbing a hand, this is the name of the hand.  If
        # None, it means that no hand is being grabbed
        self._hand_being_grabbed = None

        # Event handlers for grabbing the hands.
        self._press_id = None
        self._motion_id = None
        self._release_id = None

        # This can be 'AM' or 'PM' to distinguish the user set time
        # while grabbing the hands of the clock
        self._am_pm = 'AM'
        self.am_pm_width = 0
        self.am_pm_height = 0

    def set_display_mode(self, mode):
        """Set the type of clock to display (simple, nice, digital).
        'mode' is one of MODE_XXX_CLOCK constants.
        """
        self._mode = mode

    def _size_allocate_cb(self, widget, allocation):
        """We know the size of the widget on the screen, so we keep
        the parameters which are important for our rendering (center
        of the clock, radius).
        """
        # This callback can be called when the gdk window is not yet
        # set

        # Store the measures of the clock face widget
        self._center_x = int(allocation.width / 2.0)
        self._center_y = int(allocation.height / 2.0)
        self._radius = max(min(int(allocation.width / 2.0),
                               int(allocation.height / 2.0)) - 20, 0)
        self._line_width = int(self._radius / 150)

        # lean ackground caches
        self._simple_background_cache = None
        self._nice_background_cache = None

        # The hands sizes are proportional to the radius
        self._hand_sizes['hour'] = self._radius * 0.5
        self._hand_sizes['minutes'] = self._radius * 0.8
        self._hand_sizes['seconds'] = self._radius * 0.7

        self.initialized = True

    def _draw_cb(self, widget, cr):
        """The widget is exposed and must draw itself on the graphic
        context.

        In GTK+, widgets are double-buffered. It means that an
        off-screen buffer is automatically created to draw on it
        before the expose event is called and it prevents the screen
        from flickering.
        """
        if not self.initialized:
            self.queue_resize()

        if self._mode == _MODE_NICE_CLOCK:
            if self._nice_background_cache is None:
                # Reload the svg handle
                self._svg_handle = Rsvg.Handle.new_from_file("clock.svg")
                # Draw nice clock background
                self._nice_background_cache = \
                    cr.get_target().create_similar(
                        cairo.CONTENT_COLOR_ALPHA, self._radius * 2,
                        self._radius * 2)
                cache_ctx = cairo.Context(self._nice_background_cache)
                scale_x = self._radius * 2.0 / self._svg_handle.props.width
                scale_y = self._radius * 2.0 / self._svg_handle.props.height
                matrix = cairo.Matrix(xx=scale_x, yy=scale_y)
                cache_ctx.transform(matrix)
                self._svg_handle.render_cairo(cache_ctx)

            self._draw_nice_clock(cr)
        elif self._mode == _MODE_SIMPLE_CLOCK:
            if self._simple_background_cache is None:
                # Draw simple clock background
                logging.debug('init background cache radius %s', self._radius)
                self._simple_background_cache = cr.get_target().create_similar(
                    cairo.CONTENT_COLOR_ALPHA, self._radius * 2,
                    self._radius * 2)
                cache_ctx = cairo.Context(self._simple_background_cache)
                self._draw_simple_background(cache_ctx)
                self._draw_numbers(cache_ctx)

            self._draw_simple_clock(cr)
        elif self._mode == _MODE_DIGITAL_CLOCK:
            self._draw_digital_clock(cr)
        else:
            msg = "Unknown display mode: %d." % self._mode
            raise ValueError(msg)

        return False

    def _draw_digital_clock(self, cr):
        """Draw the digital clock.
        """
        self._draw_time_scale(cr)
        self._draw_time(cr)

    def _draw_time_scale(self, cr):
        """Draw a time scale for digital clock.
        """
        # Draw scales of hours, minutes and seconds, to give the children
        # an appreciation of the time flowing...
        cr.save()
        hours_length = 2 * self._radius / 24 * self._time.hour
        minutes_length = 2 * self._radius / 60 * self._time.minute
        seconds_length = 2 * self._radius / 60 * self._time.second

        # Fill background
        cr.set_source_rgba(*style.Color(self._COLOR_WHITE).get_rgba())
        cr.rectangle(round(self._center_x - 1.1 * self._radius),
                     round(self._center_y - 0.85 * self._radius),
                     round(2.2 * self._radius),
                     round(0.65 * self._radius))
        cr.fill()

        h = round(0.15 * self._radius)
        x = round(self._center_x - self._radius)

        # Hours scale
        cr.set_source_rgba(*style.Color(self._COLOR_HOURS).get_rgba())
        y = round(self._center_y - 0.75 * self._radius)
        cr.rectangle(x, y, hours_length, h)
        cr.fill()

        # Minutes scale
        cr.set_source_rgba(*style.Color(self._COLOR_MINUTES).get_rgba())
        y = round(self._center_y - 0.60 * self._radius)
        cr.rectangle(x, y, minutes_length, h)
        cr.fill()

        # Seconds scale
        cr.set_source_rgba(*style.Color(self._COLOR_SECONDS).get_rgba())
        y = round(self._center_y - 0.45 * self._radius)
        cr.rectangle(x, y, seconds_length, h)
        cr.fill()
        cr.restore()

    def _draw_time(self, cr):
        """Draw the time in colors (digital display).
        """
        # TRANS: The format used to display the time for digital clock
        # You can add AM/PM indicator or use 12/24 format, for example
        # "%I:%M:%S %p".  See
        # http://docs.python.org/lib/module-time.html for available
        # strftime formats If the display of the time is moving
        # horizontally, it means that the glyphs of the digits used in
        # the font don't have the same width. Try to use a Monospace
        # font.  xgettext:no-python-format
        cr.save()
        markup = _('<markup>\
<span lang="en" font_desc="Sans,Monospace Bold 96">\
<span foreground="#005FE4">%I</span>:\
<span foreground="#00B20D">%M</span>:\
<span foreground="#E6000A">%S</span>%p</span></markup>')
        markup_time = self._time.strftime(markup)

        cr.set_source_rgba(*style.Color(self._COLOR_BLACK).get_rgba())
        pango_layout = PangoCairo.create_layout(cr)
        d = int(self._center_y + 0.3 * self._radius)
        pango_layout.set_markup(markup_time)
        dx, dy = pango_layout.get_pixel_size()
        pango_layout.set_alignment(Pango.Alignment.CENTER)
        cr.translate(self._center_x - dx / 2.0, d - dy / 2.0)
        PangoCairo.update_layout(cr, pango_layout)
        PangoCairo.show_layout(cr, pango_layout)
        cr.restore()

    def _draw_simple_clock(self, cr):
        """Draw the simple clock variants.
        """

        # Can be called before the cache is ready
        if self._simple_background_cache is None:
            return
        cr.save()
        # Place the simple background
        cr.translate(self._center_x - self._radius,
                     self._center_y - self._radius)
        cr.set_source_surface(self._simple_background_cache)
        cr.paint()
        cr.restore()
        self._draw_hands(cr)

    def _draw_simple_background(self, cr):
        """Draw the background of the simple clock.
        The simple clock background is a white disk, with hours and minutes
        ticks, and the hour numbers.
        """
        cr.save()
        cr.set_line_width(4 * self._line_width)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        # Simple clock background
        cr.set_source_rgba(*style.Color(self._COLOR_WHITE).get_rgba())
        cr.arc(self._radius, self._radius, self._radius - self._line_width * 2,
               0, 2 * math.pi)
        cr.fill_preserve()
        cr.set_source_rgba(*style.Color(self._COLOR_BLACK).get_rgba())
        cr.stroke()

        # Clock ticks
        for i in xrange(60):
            if i % 15 == 0:
                inset = 0.11 * self._radius
                cr.set_line_width(7 * self._line_width)
            elif i % 5 == 0:
                inset = 0.1 * self._radius
                cr.set_line_width(5 * self._line_width)
            else:
                inset = 0.05 * self._radius
                cr.set_line_width(4 * self._line_width)

            cos = math.cos(i * math.pi / 30.0)
            sin = math.sin(i * math.pi / 30.0)
            cr.move_to(int(self._radius + (self._radius - inset) * cos),
                       int(self._radius + (self._radius - inset) * sin))
            cr.line_to(int(self._radius + (self._radius - 6) * cos),
                       int(self._radius + (self._radius - 6) * sin))
            cr.stroke()
        cr.restore()

    def _draw_nice_background(self, cr):
        """Draw the nice clock background.

        The background has been loaded from the clock.svg file to a
        rsvg handle, and we just transform this handle and render it
        with cairo.
        """
        cr.save()
        cr.translate(self._center_x - self._radius,
                     self._center_y - self._radius)
        cr.set_source_surface(self._nice_background_cache)
        cr.paint()
        cr.restore()

    def _draw_nice_clock(self, cr):
        """Draw the nice clock.
        """
        cr.save()
        self._draw_nice_background(cr)
        self._draw_hands(cr)
        cr.restore()

    def _draw_hands(self, cr):
        """Draw the hands of the analog clocks.
        """
        cr.save()
        cr.translate(0, 0)

        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        # AM/PM indicator:
        cr.set_source_rgba(
            *style.Color(self._COLOR_HOURS).get_rgba())
        pango_layout = PangoCairo.create_layout(cr)
        if self._am_pm == 'AM':
            am_pm = _('<markup><span lang="en" font_desc="Sans Bold 28">\
<span foreground="white" background="black"> AM </span><span \
foreground="lightgray"> PM </span></span></markup>')
        else:
            am_pm = _('<markup><span lang="en" font_desc="Sans Bold 28">\
<span foreground="lightgray"> AM </span><span foreground="white" \
background="black"> PM </span></span></markup>')
        cr.save()
        pango_layout.set_markup(am_pm)
        self.am_pm_width, self.am_pm_height = pango_layout.get_pixel_size()
        cr.translate(- self.am_pm_width / 2.0 + self._center_x,
                     - self.am_pm_height / 2.0 +
                     (self._radius / 3) + self._center_y)
        PangoCairo.update_layout(cr, pango_layout)
        PangoCairo.show_layout(cr, pango_layout)
        cr.restore()

        # Hour hand:
        # The hour hand is rotated 30 degrees (pi/6 r) per hour +
        # 1/2 a degree (pi/360) per minute
        cr.set_source_rgba(*style.Color(self._COLOR_HOURS).get_rgba())
        cr.set_line_width(9 * self._line_width)
        cr.arc(self._center_x, self._center_y,
               5 * self._line_width, 0, 2 * math.pi)
        cr.fill_preserve()
        cr.move_to(self._center_x, self._center_y)
        sin = math.sin(self._hand_angles['hour'])
        cos = math.cos(self._hand_angles['hour'])
        cr.line_to(
            int(self._center_x + self._hand_sizes['hour'] * sin),
            int(self._center_y - self._hand_sizes['hour'] * cos))
        cr.stroke()

        # Minute hand:
        # The minute hand is rotated 6 degrees (pi/30 r) per minute
        cr.set_source_rgba(*style.Color(self._COLOR_MINUTES).get_rgba())
        cr.set_line_width(6 * self._line_width)
        cr.arc(self._center_x, self._center_y,
               4 * self._line_width, 0, 2 * math.pi)
        cr.fill_preserve()
        cr.move_to(self._center_x, self._center_y)
        sin = math.sin(self._hand_angles['minutes'])
        cos = math.cos(self._hand_angles['minutes'])
        cr.line_to(int(self._center_x + self._hand_sizes['minutes'] * sin),
                   int(self._center_y - self._hand_sizes['minutes'] * cos))
        cr.stroke()

        # When not well-synchronised, do not draw seconds hand
        if self._time.microsecond > 100000 and self._time.microsecond < 900000:
            cr.restore()
            return

        # Seconds hand:
        # Operates identically to the minute hand
        cr.set_source_rgba(*style.Color(self._COLOR_SECONDS).get_rgba())
        cr.set_line_width(2 * self._line_width)
        cr.arc(self._center_x, self._center_y,
               3 * self._line_width, 0, 2 * math.pi)
        cr.fill_preserve()
        cr.move_to(self._center_x, self._center_y)
        sin = math.sin(self._hand_angles['seconds'])
        cos = math.cos(self._hand_angles['seconds'])
        cr.line_to(int(self._center_x + self._hand_sizes['seconds'] * sin),
                   int(self._center_y - self._hand_sizes['seconds'] * cos))
        cr.stroke()
        cr.restore()

    def _draw_numbers(self, cr):
        """Draw the numbers of the hours.
        """
        cr.save()
        cr.set_source_rgba(*style.Color(self._COLOR_HOURS).get_rgba())
        pango_layout = PangoCairo.create_layout(cr)

        for i in xrange(12):
            # TRANS: The format of the font used to print hour
            # numbers, from 1 to 12.
            hour_number = _('<markup><span lang="en" \
font_desc="Sans Bold 40">%d</span></markup>') % (i + 1)
            cr.save()
            pango_layout.set_markup(hour_number)
            dx, dy = pango_layout.get_pixel_size()
            cr.translate(- dx / 2.0 + self._radius + 0.75 *
                         self._radius * math.cos((i - 2) * math.pi / 6.0),
                         - dy / 2.0 + self._radius + 0.75 * self._radius *
                         math.sin((i - 2) * math.pi / 6.0))
            PangoCairo.update_layout(cr, pango_layout)
            PangoCairo.show_layout(cr, pango_layout)
            cr.restore()
        cr.restore()

    def _dequeue_update(self):
        """Cancel the next exact second update.
        """
        if self._update_id is not None:
            GLib.source_remove(self._update_id)
            self._update_id = None

    def _requeue_update(self):
        """Queue an update for as close as possible to the next exact
        second, plus two milliseconds.
        """
        self._dequeue_update()

        interval = (1000000 - (GLib.get_real_time() % 1000000)) / 1000 + 2
        self._update_id = GLib.timeout_add(interval, self._update_cb)

    def _update_cb(self):
        """Called as close as possible to exact second; to update the
        time, tick, calculate hand angles, queue a redraw, emit
        changed minute signal, and requeue the update for next exact
        second.
        """
        # update the time and force a redraw of the clock
        self._time = datetime.now()

        # When well-synchronised, then tick
        if self._time.microsecond < 100000 or self._time.microsecond > 900000:
            self._tick()

        self._hand_angles['hour'] = (math.pi / 6 * (self._time.hour % 12) +
                                     math.pi / 360 * self._time.minute)

        self._hand_angles['minutes'] = math.pi / 30 * self._time.minute
        self._hand_angles['seconds'] = math.pi / 30 * self._time.second

        if self._time.hour < 12:
            self._am_pm = 'AM'
        else:
            self._am_pm = 'PM'

        self.queue_draw()

        # When the minutes change, we raise the 'time_minute'
        # signal. We can't test on 'self._time.second == 0' for
        # instance because Gtk timer does not guarantee to call us
        # every seconds.
        if self._old_minute != self._time.minute:
            self.emit("time_minute")
            self._old_minute = self._time.minute

        # Keep running this update as long as the clock is active
        # (ie. visible) or the mode changes to dragging the hands of
        # the clock
        if self._active and not self.grab_hands_mode:
            self._requeue_update()

        self._update_id = None
        return False

    def _get_time_from_hands_angles(self):
        """Uses the angles of the hands to generate hours and minute
        time. Due to the small movement of the hour hand the minute hand
        position must be used to correctly round/floor to the correct hour.
        """
        if self._hand_angles['minutes'] > math.pi / 30.0:
            hour = int(
                (self._hand_angles['hour'] * 12) / (math.pi * 2)) % 12
        else:
            hour = int(
                round((self._hand_angles['hour'] * 12) / (math.pi * 2))) % 12
        if self._am_pm == 'PM':
            hour += 12

        minute = int(
            round((self._hand_angles['minutes'] * 60) / (math.pi * 2)))
        # Second is not used by speech or to display time in full
        # letters, so we avoid that calculation
        second = 0

        return datetime(self._time.year, self._time.month, self._time.day,
                        hour=hour, minute=minute, second=second)

    def get_time(self):
        """Public access to the time member of the clock face. In grab
        hands mode, return the time according to the position of the
        clock hands.
        """
        if self.grab_hands_mode:
            return self._get_time_from_hands_angles()
        else:
            return self._time

    def _get_active(self):
        """Get the activity status of the clock. When active, the
        clock face redraws itself. When inactive, we do nothing to
        save resources.
        """
        return self._active

    def _set_active(self, active):
        """Set the activity state of the clock face. When Sugar
        reactivates the clock, we start a timer to be called every
        second and update the clock.
        """
        if self._active == active:
            return

        self._active = active

        if active:
            # We must redraw the clock...
            self._update_cb()

            # And update again the clock on every second tick.
            self._requeue_update()
        else:
            self._dequeue_update()

    active = property(_get_active, _set_active)

    def toggle_am_pm(self):
        if self._am_pm == 'AM':
            self._am_pm = 'PM'
        else:
            self._am_pm = 'AM'

    def change_grab_hands_mode(self, toggle_grab):
        """Connect or disconnect the callbacks for to grab the hands
        of the clock.
        """
        self.grab_hands_mode = toggle_grab

        if toggle_grab:
            self._press_id = self.connect("button-press-event",
                                          self._press_cb)
            self._motion_id = self.connect("motion-notify-event",
                                           self._motion_cb)
            self._release_id = self.connect("button-release-event",
                                            self._release_cb)

            # Put hand cursor
            self.get_window().set_cursor(
                Gdk.Cursor.new(Gdk.CursorType.HAND2))

        else:
            self.disconnect(self._press_id)
            self.disconnect(self._motion_id)
            self.disconnect(self._release_id)

            # Put original cursor again
            self.get_window().set_cursor(
                Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR))

            # Update again the clock on every second tick
            self._requeue_update()

        self.emit("time_minute")

    def _press_cb(self, widget, event):
        _pointer, mouse_x, mouse_y, state = event.window.get_pointer()

        # Only pay attention to the button 1
        if not state & Gdk.ModifierType.BUTTON1_MASK:
            return

        # Calculate the angle from the center of the clock to the
        # mouse pointer
        adjacent = mouse_x - self._center_x
        opposite = -1 * (mouse_y - self._center_y)
        pointer_angle = math.atan2(adjacent, opposite)

        # Calculate the distance from the center of the clock to the
        # mouse pointer
        pointer_distance = math.hypot(adjacent, opposite)

        # If the angle is negative, convert it to the equal angle
        # between 0 and 2 PI
        if pointer_angle < 0:
            pointer_angle += math.pi * 2

        def in_range(hand_angle, angle):
            """Return True if the given angle is in a range of the
            hand_angle +- the angle tolerance.
            """
            # This is the normalized angle, the equal angle that is
            # minor than 2 PI
            hand_normal = (hand_angle -
                           (math.pi * 2) * int(hand_angle / (math.pi * 2)))

            return (hand_normal >= angle - _ANGLE_TOLERANCE and
                    hand_normal < angle + _ANGLE_TOLERANCE)

        # Check if we can start grabbing a hand of the clock:
        for hand in ['hour', 'minutes', 'seconds']:
            if in_range(self._hand_angles[hand], pointer_angle):
                if pointer_distance <= self._hand_sizes[hand]:
                    self._hand_being_grabbed = hand
                    break

        # Toggle AM or PM if clock face AM/PM area pressed
        if self._hand_being_grabbed is None and \
                mouse_x > self._center_x - self.am_pm_width / 2 and \
                mouse_x < self._center_x + self.am_pm_width / 2 and \
                mouse_y > self._center_y + self._radius / 3 - \
                self.am_pm_height and \
                mouse_y < self._center_y + self._radius / 3 + \
                self.am_pm_height:

            self.toggle_am_pm()

            self.emit("time_minute")
            self.queue_draw()

    def _motion_cb(self, widget, event):
        if self._hand_being_grabbed is None:
            return

        if event.is_hint:
            _pointer, mouse_x, mouse_y, state = event.window.get_pointer()
        else:
            mouse_x = event.x
            mouse_y = event.y
            state = event.state

        # Only pay attention to the button 1
        if not state & Gdk.ModifierType.BUTTON1_MASK:
            return

        # Calculate the angle from the center of the clock to the
        # mouse pointer
        adjacent = mouse_x - self._center_x
        opposite = -1 * (mouse_y - self._center_y)
        pointer_angle = math.atan2(adjacent, opposite)

        # If the angle is negative, convert it to the equal angle
        # between 0 and 2 PI
        if pointer_angle < 0:
            pointer_angle += math.pi * 2

        # Auto spin hour hand and snap minute hand when minutes dragged
        if self._hand_being_grabbed == 'minutes':
            pointer_angle = int((pointer_angle * 60) / (
                math.pi * 2)) * (math.pi * 2) / 60.0
            self._hand_angles['hour'] += (
                pointer_angle - self._hand_angles['minutes']) / 12.0
            if pointer_angle - self._hand_angles['minutes'] > math.pi:
                self._hand_angles['hour'] -= math.pi * 2 / 12.0
            elif pointer_angle - self._hand_angles['minutes'] < -math.pi:
                self._hand_angles['hour'] += math.pi * 2 / 12.0
            # Toggle AM/PM as needed
            if self._hand_angles['hour'] >= math.pi * 2:
                self._hand_angles['hour'] -= math.pi * 2
                self.toggle_am_pm()
            elif self._hand_angles['hour'] < 0:
                self._hand_angles['hour'] += math.pi * 2
                self.toggle_am_pm()

        # Auto spin and snap minute hand when hour hand dragged
        if self._hand_being_grabbed == 'hour':
            tmp = self._hand_angles['hour'] * 12.0
            while tmp >= math.pi * 2:
                tmp -= math.pi * 2
            self._hand_angles['minutes'] = int(
                (tmp * 60) / (math.pi * 2)) * (math.pi * 2) / 60.0
            # Toggle AM/PM as needed
            if abs(self._hand_angles['hour'] - pointer_angle) > math.pi:
                self.toggle_am_pm()

        # Update the angle of the hand being grabbed
        self._hand_angles[self._hand_being_grabbed] = pointer_angle

        # Force redraw of the clock:
        self.queue_draw()

    def _release_cb(self, widget, event):
        if self._hand_being_grabbed is None:
            return

        if self._hand_being_grabbed in ['hour', 'minutes']:
            self.emit("time_minute")

        self._hand_being_grabbed = None
        self.queue_draw()

    def _tick_message_cb(self, bus, message):
        """On tick end of stream, stop, seek to start of file, and
        prepare for playing using PAUSED.  Minimises latency between
        clock second hand redraw and sound."""
        if message.type == Gst.MessageType.EOS:
            self._player.set_state(Gst.State.NULL)
            self._player.seek_simple(Gst.Format.TIME,
                                     Gst.SeekFlags.FLUSH,
                                     0 * Gst.SECOND)
            self._player.set_state(Gst.State.PAUSED)
        return True

    def _get_ticking(self):
        return self._ticking

    def _set_ticking(self, ticking):

        # Start ticking sound player
        if not self._ticking and ticking:
            self._player = Gst.ElementFactory.make('playbin', 'Player')
            self._player.set_property('uri', 'file://%s' %
                                      os.path.join(activity.get_bundle_path(),
                                                   'sounds', 'tick.wav'))
            self._player.set_state(Gst.State.PAUSED)

            bus = self._player.get_bus()
            bus.add_signal_watch()
            bus.connect('message', self._tick_message_cb)

        # Stop ticking sound player
        if self._ticking and not ticking:
            self._player.set_state(Gst.State.NULL)
            self._player = None

        self._ticking = ticking

    ticking = property(_get_ticking, _set_ticking)

    def _tick(self):
        """Make a tick sound.
        Player is in PAUSED state, so ready to go."""
        if self._ticking:
            self._player.set_state(Gst.State.PLAYING)
