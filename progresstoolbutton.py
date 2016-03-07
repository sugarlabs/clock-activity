#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016  Utkarsh Tiwari
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Contact information:
# Utkarsh Tiwari    iamutkarshtiwari@gmail.com

"""
BETA
"""

import logging

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.icon import get_surface
from sugar3.graphics.palette import Palette, ToolInvoker


def _add_accelerator(tool_button):
    if not tool_button.props.accelerator or not tool_button.get_toplevel() or \
            not tool_button.get_child():
        return

    # TODO: should we remove the accelerator from the prev top level?
    if not hasattr(tool_button.get_toplevel(), 'sugar_accel_group'):
        logging.debug('No Gtk.AccelGroup in the top level window.')
        return

    accel_group = tool_button.get_toplevel().sugar_accel_group
    keyval, mask = Gtk.accelerator_parse(tool_button.props.accelerator)
    # the accelerator needs to be set at the child, so the Gtk.AccelLabel
    # in the palette can pick it up.
    tool_button.get_child(
    ).add_accelerator('clicked', accel_group, keyval, mask,
                      Gtk.AccelFlags.LOCKED | Gtk.AccelFlags.VISIBLE)


def _hierarchy_changed_cb(tool_button, previous_toplevel):
    _add_accelerator(tool_button)


def setup_accelerator(tool_button):
    _add_accelerator(tool_button)
    tool_button.connect('hierarchy-changed', _hierarchy_changed_cb)


class ProgressToolButton(Gtk.ToolButton):
    """Display the progress filling the ToolButton icon.

    Call update(progress) with the new progress to update the ToolButton icon.

    The direction defaults to 'vertical', in which case the icon is
    filled from bottom to top.  If direction is set to 'horizontal',
    it will be filled from right to left or from left to right,
    depending on the system's language RTL setting.

    """
    __gtype_name__ = 'SugarProgressToolButton'

    def __init__(self, icon_name=None, pixel_size=None, direction='vertical', **kwargs):
        self._accelerator = None
        self._tooltip = None
        self._palette_invoker = ToolInvoker()
        self._progress = 0.0
        self._icon_name = icon_name
        self._pixel_size = pixel_size
        self._direction = direction

        GObject.GObject.__init__(self, **kwargs)

        self._hide_tooltip_on_click = True
        self._palette_invoker.attach_tool(self)

        self._stroke = get_surface(
            icon_name=self._icon_name, width=self._pixel_size, height=self._pixel_size,
            stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
            #stroke_color=style.COLOR_WHITE.get_svg(),
            fill_color=style.COLOR_TRANSPARENT.get_svg())

        self._fill = get_surface(
            icon_name=self._icon_name, width=self._pixel_size, height=self._pixel_size,
            stroke_color=style.COLOR_TRANSPARENT.get_svg(),
            fill_color=style.COLOR_WHITE.get_svg())

        self.get_child().connect('can-activate-accel',
                             self.__button_can_activate_accel_cb)

        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def __button_can_activate_accel_cb(self, button, signal_id):
        # Accept activation via accelerators regardless of this widget's state
        return True

    def set_tooltip(self, tooltip):
        """ Set a simple palette with just a single label.
        """
        if self.palette is None or self._tooltip is None:
            self.palette = Palette(tooltip)
        elif self.palette is not None:
            self.palette.set_primary_text(tooltip)

        self._tooltip = tooltip

        # Set label, shows up when toolbar overflows
        Gtk.ToolButton.set_label(self, tooltip)

    def get_tooltip(self):
        return self._tooltip

    tooltip = GObject.property(type=str, setter=set_tooltip,
                               getter=get_tooltip)

    def get_hide_tooltip_on_click(self):
        return self._hide_tooltip_on_click

    def set_hide_tooltip_on_click(self, hide_tooltip_on_click):
        if self._hide_tooltip_on_click != hide_tooltip_on_click:
            self._hide_tooltip_on_click = hide_tooltip_on_click

    hide_tooltip_on_click = GObject.property(
        type=bool, default=True, getter=get_hide_tooltip_on_click,
        setter=set_hide_tooltip_on_click)

    def set_accelerator(self, accelerator):
        self._accelerator = accelerator
        setup_accelerator(self)

    def get_accelerator(self):
        return self._accelerator

    accelerator = GObject.property(type=str, setter=set_accelerator,
                                   getter=get_accelerator)

    def set_icon_name(self, icon_name):
        icon = Icon(icon_name=icon_name)
        self.set_icon_widget(icon)
        icon.show()

    def get_icon_name(self):
        if self.props.icon_widget is not None:
            return self.props.icon_widget.props.icon_name
        else:
            return None

    icon_name = GObject.property(type=str, setter=set_icon_name,
                                 getter=get_icon_name)

    def create_palette(self):
        return None

    def get_palette(self):
        return self._palette_invoker.palette

    def set_palette(self, palette):
        self._palette_invoker.palette = palette

    palette = GObject.property(
        type=object, setter=set_palette, getter=get_palette)

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def do_draw(self, cr):
        if self._progress > 0:
            self._stroke = get_surface(
                icon_name=self._icon_name, width=self._pixel_size, height=self._pixel_size,
                stroke_color=style.COLOR_WHITE.get_svg(),
                fill_color=style.COLOR_TRANSPARENT.get_svg())
        else:
            self._stroke = get_surface(
                icon_name=self._icon_name, width=self._pixel_size, height=self._pixel_size,
                stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
                fill_color=style.COLOR_TRANSPARENT.get_svg())

        allocation = self.get_allocation()

        # Center the graphic in the allocated space.
        margin_x = (allocation.width - self._stroke.get_width()) / 2
        margin_y = (allocation.height - self._stroke.get_height()) / 2
        cr.translate(margin_x, margin_y)

        # Paint the fill, clipping it by the progress.
        x_, y_ = 0, 0
        width, height = self._stroke.get_width(), self._stroke.get_height()
        if self._direction == 'vertical':  # vertical direction, bottom to top
            y_ = self._stroke.get_height()
            height *= self._progress * -1
        else:
            rtl_direction = \
                Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL
            if rtl_direction:  # horizontal direction, right to left
                x_ = self._stroke.get_width()
                width *= self._progress * -1
            else:  # horizontal direction, left to right
                width *= self._progress

        cr.rectangle(x_, y_, width, height)
        cr.clip()
        cr.set_source_surface(self._fill, 0, 0)
        cr.paint()

        # Paint the stroke over the fill.
        cr.reset_clip()
        cr.set_source_surface(self._stroke, 0, 0)
        cr.paint()
        return False

    def do_clicked(self):
        if self._hide_tooltip_on_click and self.palette:
            self.palette.popdown(True)

    def update(self, progress):
        self._progress = progress
