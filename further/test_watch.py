# -*- coding: utf-8 -*-
""" DisplayThread Class

This module contains the DisplayThread class and
an associated example main function.

The DisplayThread Class is intended for
use on Raspberry Pi computers connected to an
Adafruit 8x8 LED Matrix.

The class defines various display options, selected
using an identifier (integer value) in a file.

The current options defined are:
0) 4 x 2column CPU Core Percentage Use
1) Blocked Average Load with Idle I animation
2) Line Graph Temperature


This class uses threading.Thread to inherit from.

The default timing is to update every second.

Note that this is intended for Raspberry Pi systems
and requires the vcgencmd to be available."""

import os
import sys
import time
import threading
import Image
import ImageDraw
import psutil
import subprocess
from Adafruit_LED_Backpack import Matrix8x8
from collections import deque


class LoadThread(threading.Thread):
    """ Init takes in the default stopcondition and
        the target display matrix """

    def __init__(self, stopcond, matrixdisplay):
        super(LoadThread, self).__init__()
        self.stopcond = False
        self.display = matrixdisplay
        self.images = {0: Image.new('1', (8, 8)), 1: Image.new('1', (8, 8))}
        self.current = 0
        self.metric = 0
        self.temp = deque(8 * [0])
        self.mintemp = 0
        self.maxtemp = 85
        self.cpu = deque(8 * [0])
        self.mincpu = 0
        self.maxcpu = 100
        self.priorout = 0
        self.priorin = 0

    def createImage(self):
        """ Create Idle Image """
        draw = ImageDraw.Draw(self.images[self.current])
        # draw.rectangle((0,0,7,7),outline=255, fill=0)
        draw.line((1, 1, 6, 1), fill=255)
        draw.line((1, 6, 6, 6), fill=255)
        draw.rectangle((3, 2, 4, 5), fill=255)
        self.current = not self.current
        draw = ImageDraw.Draw(self.images[self.current])
        # draw.rectangle((0,0,7,7),outline=255, fill=0)
        draw.line((1, 1, 1, 6), fill=255)
        draw.line((6, 1, 6, 6), fill=255)
        draw.rectangle((2, 3, 5, 4), fill=255)

    def updateMetric(self):
        if os.path.exists("metric.txt"):
            file = open("metric.txt")
            temp = int(file.read())
            self.metric = temp
            file.close()

    def run(self):
        """ Run method which loops until the stopcondition
        is set. It will read the average load of the system
        and call writeMinute to write out information."""
        self.createImage()
        self.updateMetric()
        loop = 1
        while not self.stopcond:
            # print loop
            if loop % 20 == 0:
                self.updateMetric()
                loop = 0
            # av1, av2, av3 = os.getloadavg()
            if self.metric == 0:
                cpupercent = psutil.cpu_percent(interval=1, percpu=True)
                self.writeCpus(cpupercent)
            if self.metric == 1:
                av1, av2, av3 = os.getloadavg()
                self.writeMinute(av1)
                time.sleep(1)
            if self.metric == 2:
                self.temp.popleft()
                self.temp.append(self.get_temperature())
                self.writeline(self.temp, self.mintemp, self.maxtemp)
                time.sleep(1)
            if self.metric == 3:
                self.cpu.popleft()
                self.cpu.append(psutil.cpu_percent(percpu=False))
                self.writeline(self.cpu, self.mincpu, self.maxcpu)
                time.sleep(1)
            if self.metric == 4: 
                network = psutil.net_io_counters(pernic=True)
                self.writeNetwork(network)
                time.sleep(1)
            if self.metric == 5:
                cpupercent = psutil.cpu_percent(interval=1, percpu=True)
                temp = self.get_temperature()
                self.temp.popleft()
                self.temp.append(temp)
                network = psutil.net_io_counters(pernic=True)
                memory = psutil.virtual_memory()
                self.writeMultiMetric(cpupercent, temp,self.mintemp, self.maxtemp,network,memory)

            # print " Load average: %.2f %.2f %.2f " % (av1, av2, av3)
            loop = loop + 1
            # time.sleep(1)

    
    def writeMultiMetric(self, cpupercent, temp, tempmin,tempmax,network,memory):

        cpus = len(cpupercent)
        width = 4 / cpus
        perVal = [int(round(x * 8.0 / 100.0)) for x in cpupercent]
        # print loadVal
        self.display.clear()
        bars = Image.new('1', (8, 8))
        draw = ImageDraw.Draw(bars)
        # print cpupercent
        # print perVal
        for cpu in range(cpus):
            draw = ImageDraw.Draw(bars)
            if perVal[cpu] > 0:
                draw.line((0 + (width * cpu),
                           7, 0 + (width * cpu), 8 - perVal[cpu]), fill=255)
            else:
                draw.line((0 + (width * cpu),
                           7, 0 + (width * cpu), 8 - perVal[cpu]), fill=0)
        packetout = network['eth0'][0]
        packetin = network['eth0'][1]
        displayin = int((packetin - self.priorin) * 8.0/10000.0)
        displayout = int((packetout - self.priorout) * 8.0/10000.0)
        self.priorin = packetin
        self.priorout = packetout
        if displayin > 0:
            draw.line((4,7,4,8-displayin),fill=255)
        if displayout > 0:
            draw.line((5,7,4,8-displayout),fill=255)
        memorydisp = int(round(memory[2] * 8.0 / 100.0))
        draw.line((6,7,6,8-memorydisp),fill=255)
        tempdisp = int(round(temp * 8.0 / 100.0))
        draw.line((7,7,7,8-tempdisp),fill=255)
        self.display.set_image(bars)
        self.display.write_display()

    def writeCpus(self, cpupercent):

        cpus = len(cpupercent)
        width = 8 / cpus
        perVal = [int(round(x * 8.0 / 100.0)) for x in cpupercent]
        # print loadVal
        self.display.clear()
        bars = Image.new('1', (8, 8))
        draw = ImageDraw.Draw(bars)
        # print cpupercent
        # print perVal
        for cpu in range(cpus):
            draw = ImageDraw.Draw(bars)
            if perVal[cpu] > 0:
                draw.line((0 + (width * cpu),
                           7, 0 + (width * cpu), 8 - perVal[cpu]), fill=255)
                draw.line((1 + (width * cpu), 7,
                           1 + (width * cpu), 8 - perVal[cpu]), fill=255)
            else:
                draw.line((0 + (width * cpu),
                           7, 0 + (width * cpu), 8 - perVal[cpu]), fill=0)
                draw.line((1 + (width * cpu),
                           7, 1 + (width * cpu), 8 - perVal[cpu]), fill=0)
        self.display.set_image(bars)
        self.display.write_display()

    def writeNetwork(self, network):
        packetout = network['eth0'][0]
        packetin = network['eth0'][1]
        displayin = int((packetin - self.priorin) * 8.0/10000.0)
        displayout = int((packetout - self.priorout) * 8.0/10000.0)
        #print "%s %s %s %s %s %s" % (packetin, packetout, displayin, displayout, self.priorin, self.priorout)
        self.priorin = packetin
        self.priorout = packetout
        self.display.clear()
        bars = Image.new('1', (8, 8))
        draw = ImageDraw.Draw(bars)
        if displayin > 0:
            draw.rectangle([0,7,2,8-displayin],fill=255)
        if displayout > 0:
            draw.rectangle([5,7,7,8-displayout],fill=255)
        self.display.set_image(bars)
        self.display.write_display()

    def writeline(self, linevalues, minscalevalue, maxscalevalue):
        points = len(linevalues)
        perVal = [int(round(x * 8.0 / (maxscalevalue - minscalevalue)))
                  for x in linevalues]
        self.display.clear()
        bars = Image.new('1', (8, 8))
        draw = ImageDraw.Draw(bars)
        for point in range(points):
            draw = ImageDraw.Draw(bars)
            draw.point([point, 8 - perVal[point]], fill=255)
        self.display.set_image(bars)
        self.display.write_display()

    def get_temperature(self):
        try:
            s = subprocess.check_output(
                    ['/opt/vc/bin/vcgencmd', 'measure_temp'])
            return float(s.split('=')[1][:-3])
        except Exception as inst:
            return 0

    def writeMinute(self, averageLoad):
        """ This will take an float average load value and scale it to
        fit on a 8x8 matrix which will fill in rows until full. """
        loadVal = int(round(averageLoad * 16.0))
        # print loadVal
        if loadVal > 0:
            self.display.clear()
            current = 1
            for x in range(8):
                for y in range(7, -1, -1):
                    if current <= loadVal:
                        self.display.set_pixel(x, y, 1)
                    current = current + 1
            self.display.write_display()
        else:
            self.display.clear()
            self.display.set_image(self.images[self.current])
            self.current = not self.current
            self.display.write_display()

    def stopthread(self):
        """ Called to stop the thread by setting stopcond to true."""
        self.stopcond = True


if __name__ == "__main__":
    # Initialise Display and thread.
    displays = Matrix8x8.Matrix8x8()
    displays.begin()
    displays.clear()
    displays.write_display()
    thread_watch = LoadThread(False, displays)
    thread_watch.start()
    try:  # Loop until keyboard interrupt
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        thread_watch.stopthread()
    thread_watch.join()
    # Clear display
    displays.clear()
    displays.write_display()
