#!/usr/bin/env python3

import re

from asciimatics.effects import Julia, Clock, Print
from asciimatics.widgets import Frame, TextBox, Layout, Label, Divider, Text, \
    CheckBox, RadioButtons, Button, PopUpDialog
from asciimatics.renderers import BarChart, VBarChart, FigletText

from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.exceptions import ResizeScreenError, NextScene, StopApplication, \
    InvalidFields
from opcua import Client
from threading import Thread
import sys
import math
import time


class CustomBarChart(BarChart):
    """
    Renderer to create a horizontal bar chart using the specified functions as inputs for each
    entry.  Can be used to chart distributions or for more graphical effect - e.g. to imitate a
    sound equalizer or a progress indicator.
    """

    def __init__(self, height, width, functions, char="#", colour=Screen.COLOUR_GREEN,
                 bg=Screen.COLOUR_BLACK, gradient=None, scale=None, axes=BarChart.Y_AXIS,
                 intervals=None, labels=False, border=True, keys=None, gap=None):
        self.width = width
        self.height = height
        super().__init__(
            height, width, functions, char, colour, bg, gradient, scale, axes, intervals, labels, border,
            keys, gap)


    def _render_now(self):
        int_h, int_w, start_x, start_y = self._setup_chart()

        # Make room for the keys if supplied.
        if self._keys:
            max_key = max([len(x) for x in self._keys])
            key_x = start_x
            int_w -= 15#max_key + 10
            start_x += 15#max_key + 10

        # Now add the axes - resizing chart space as required...
        if (self._axes & BarChart.X_AXIS) > 0:
            int_h -= 1

        if (self._axes & BarChart.Y_AXIS) > 0:
            int_w -= 1
            start_x += 1

        if self._labels:
            int_h -= 1

        # Use given scale or whatever space is left in the grid
        scale = int_w if self._scale is None else self._scale

        if self._axes & BarChart.X_AXIS:
            self._write(self._axes_lines.h * int_w, start_x, start_y + int_h)
        if self._axes & BarChart.Y_AXIS:
            for line in range(int_h):
                self._write(self._axes_lines.v, start_x - 1, start_y + line)
        if self._axes & BarChart.BOTH == BarChart.BOTH:
            self._write(self._axes_lines.up_right, start_x - 1, start_y + int_h)

        if self._labels:
            pos = start_y + int_h
            if self._axes & BarChart.X_AXIS:
                pos += 1

            self._write("0", start_x, pos)
            text = str(scale)
            self._write(text, start_x + int_w - len(text), pos)

        # Now add any interval markers if required...
        if self._intervals is not None:
            i = self._intervals
            while i < scale:
                x = start_x + int(i * int_w / scale) - 1
                for line in range(int_h):
                    self._write(self._axes_lines.v_inside, x, start_y + line)
                self._write(self._axes_lines.h_up, x, start_y + int_h)
                if self._labels:
                    val = str(i)
                    self._write(val, x - (len(val) // 2), start_y + int_h + 1)
                i += self._intervals

        # Allow double-width bars if there's space.
        bar_size = 2 if int_h >= (3 * len(self._functions)) - 1 else 1

        gap = self._gap
        if self._gap is None:
            gap = 0 if len(self._functions) <= 1 else (int_h - (bar_size * len(
                self._functions))) / (len(self._functions) - 1)


        # Now add the bars...
        for i, fn in enumerate(self._functions):
            bar_len = int(fn() * int_w / scale)
            y = start_y + (i * bar_size) + int(i * gap)


            # First draw the key if supplied
            if self._keys:
                key = self._keys[i]
                pos = max_key - len(key)
                self._write(key, key_x + pos, y)
                self._write(str(fn()), key_x + pos, y+1)



            # Now draw the bar
            colour = self._colours[i % len(self._colours)]
            bg = self._bgs[i % len(self._bgs)]
            if self._gradient:
                # Colour gradient required - break down into chunks for each colour.
                last = 0
                size = 0
                for threshold, colour, bg in self._gradient:
                    value = int(threshold * int_w / scale)
                    if value - last > 0:
                        # Size to fit the available space
                        size = value if bar_len >= value else bar_len
                        if size > int_w:
                            size = int_w
                        for line in range(bar_size):
                            self._write(
                                self._char * (size - last), start_x + last, y + line, colour, bg=bg)

                    # Stop if we reached the end of the line or the chart
                    if bar_len < value or size >= int_w:
                        break
                    last = value
            else:
                # Solid colour - just write the whole block out.
                for line in range(bar_size):
                    self._write(self._char * bar_len, start_x, y + line, colour, bg=bg)

        return self._plain_image, self._colour_map

group1_list = []
class SubHandler(object):

    """
    Subscription Handler. To receive events from server for a subscription
    data_change and event methods are called directly from receiving thread.
    Do not do expensive, slow or network operation there. Create another 
    thread if you need to do such a thing
    """

    def datachange_notification(self, node, val, data):
        print("Python: New data change event", node, val)
        global group1_list
        group1_list = val

    def event_notification(self, event):
        print("Python: New event", event)

def connect():
    client = Client("opc.tcp://192.168.1.138:4840")
    # client = Client("opc.tcp://admin@localhost:4840/freeopcua/server/") #connect using a user
    client.connect()

    dataList = client.get_node('ns=2;s=group1')
    # subscribing to a variable node
    handler = SubHandler()
    sub = client.create_subscription(500, handler)
    handle = sub.subscribe_data_change(dataList)
    sub.subscribe_events()

        

def wv1(x, r):
    return lambda: (math.floor((1 + math.sin(math.pi * (2*time.time()+x) / 5)*r)*100))/100

class ChartFrame(Frame):
    def __init__(self, screen, x, y, chartName, scale, intervals, fun, label):
        super(ChartFrame, self).__init__(screen, 0, 0,
                                         name=chartName,
                                         has_shadow=True,
                                         x=x, y=y, reduce_cpu=True
        )

        hchartA = CustomBarChart(6, 80, [fun],
            gradient=[
                (5, Screen.COLOUR_WHITE, Screen.COLOUR_WHITE),
                (15, Screen.COLOUR_YELLOW, Screen.COLOUR_YELLOW),
                (30, Screen.COLOUR_RED, Screen.COLOUR_RED),
            ],
            scale=scale, axes=BarChart.X_AXIS, intervals=intervals, labels=True, border=True, keys=[label])
        
        self.add_effect(Print(screen, hchartA, x=x, y=y, transparent=False, speed=1))


def demo(screen, scene):
    scenes = []
    value = wv1(1, 30)
    def getValue(i):
        return lambda: group1_list[i]
    
    effects = [
        Julia(screen),
        ChartFrame(screen, 2, 2, 'Frequency', scale=40, intervals=10, fun=getValue(0), label='Hz'),
        ChartFrame(screen, 2, 9, 'Volts', scale=240, intervals=60, fun=getValue(1), label='Volts'),
        ChartFrame(screen, 2, 16, 'Kw', scale=1000, intervals=200, fun=getValue(2), label='Kw'),
        ChartFrame(screen, 2, 23, 'Rpm', scale=1000, intervals=200, fun=getValue(3), label='Rpm'),
        ChartFrame(screen, 2, 30, 'Amp', scale=5, intervals=1, fun=getValue(3), label='Amp'),
        ChartFrame(screen, 2, 37, 'AmpCop', scale=5, intervals=1, fun=getValue(5), label='AmpCop'),
        ChartFrame(screen, 2, 44, 'Load%', scale=100, intervals=10, fun=getValue(6), label='Load %'),
    ]
    scenes.append(Scene(effects, -1))

    screen.play(scenes, stop_on_resize=True, start_scene=scene)



last_scene = None
connect()
while True:
    try:
        Screen.wrapper(demo, catch_interrupt=False, arguments=[last_scene])
        sys.exit(0)
    except ResizeScreenError as e:
        last_scene = e.scene
