#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
#
# termiteOS
# Copyright (c) July 2018 Nacho Mas
from termiteOS.config import *

#virtual class. It must be used to derive the actual driver class
#which implemente the motor driver
class axis(object):
    def __init__(self, name):
        self.log = True
        self.setName(name)
        self.pointError = ephem.degrees(0)
        self.timestepMax = 0
        self.timestepMin = 0
        self.timestep = self.timestepMax
        self.acceleration = ephem.degrees(engine['acceleration'])
        self.a = ephem.degrees(0)
        self.v = ephem.degrees(0)
        self.vmax = ephem.degrees(ephem.degrees('10:00:00'))
        self.beta = ephem.degrees(0)
        self.beta_target = ephem.degrees(0)
        self.t2target = 0
        self._vmax = self.v
        self.vtracking = 0
        self.slewend = False
        self.RUN = True
        self.T0 = time.time()

    def setName(self, name):
        self.name = name
        if self.log:
            self.logfile = open(str(self.name) + ".log", 'w')
            line = "T timestep timesleep vmax beta_target beta v a motorBeta steps\r\n"
            self.logfile.write(line)

    def slew(self, beta, blocking=False):

        self.slewend = False
        self.beta_target = ephem.degrees(beta)
        if not blocking:
            return
        while not self.slewend:
            time.sleep(1)

    def track(self, v):
        #not needed now. If not slewing is tracking
        return
        #print "TRACKING START"
        self.vtracking = ephem.degrees(v)

    def sync(self, b):
        self.beta_target = ephem.degrees(b)
        self.beta = ephem.degrees(b)

    #Main loop thread
    @threaded
    def run(self):
        self.T = time.time()
        while self.RUN:
            #estimate the timestep based on the error point
            if self.v != 0:
                self.timesleep = abs(float(self.pointError) / (self.v))
                if self.timesleep < self.timestepMin:
                    self.timesleep = self.timestepMin
                if self.timesleep > self.timestepMax:
                    self.timesleep = self.timestepMax
            else:
                self.timesleep = self.timestepMax

            #now calculate the actual timestep
            now = time.time()
            deltaT = now - self.T

            #print self.name,self.timestep,deltaT,self.v
            self.timestep = deltaT
            if self.slewend:
                steps = self.tracktick()
            else:
                steps = self.slewtick()

            self.doSteps(steps)
            self.T = now
            time.sleep(self.timesleep)
        print "rampsThread ended"

    def tracktick(self):
        steps = self.vtracking * self.timestep
        self.beta = self.beta + steps
        self.beta_target = self.beta
        self.v = self.vtracking
        return steps

    #NOT IN USE.
    #Change speed smoothly
    def tracktickSmooth(self):
        self.vdelta = self.vtracking - self.v
        sign = math.copysign(1, self.vdelta)
        self.beta_slope = (self.v * self.v) / (2 * self.acceleration)
        self.t_slope = self.v / self.acceleration
        self.a = self.acceleration * sign
        self.v = self.v + self.a * self.timestep

        #check if already at max speed
        if abs(self.v - self.vtracking) <= 0.01:
            self.v = self.vtracking
            self.a = 0

        steps = self.v * self.timestep + self.a * (
            self.timestep * self.timestep) / 2
        self.beta = self.beta + steps
        #print self.beta,self.v,self.a,steps

        return steps

    def slewtick(self):
        if self.slewend:
            #This change to tracktick() in run()
            steps = 0
            return steps

        #Update target position with the tracking speed
        self.beta_target = self.beta_target + self.vtracking * self.timestep

        self.delta = self.beta_target - self.beta
        sign = math.copysign(1, self.delta)
        v_sign = math.copysign(1, self.v)

        self.beta_slope = (self.v * self.v) / (2 * self.acceleration)
        self.t_slope = self.v / self.acceleration

        #check if arrived to target
        #if  abs(self.delta) <= self.pointError and abs(self.v)<=self.pointError:
        if abs(self.delta) <= self.pointError:
            self.slewend = True
            self.v = self.vtracking
            self.a = 0
            steps = self.delta
            self.beta = self.beta + steps
            self.track(self.vtracking)
            #self.beta=ephem.degrees(self.beta_target)
            print self.name, "Slew End", ephem.degrees(self.beta)
            return steps

        #check if it is time to deccelerate
        if abs(self.delta) - self.beta_slope <= 0:
            self.a = -self.acceleration * sign
            #print self.name,"Decelerating:",self.a
        else:
            if abs(self.v) < abs(self._vmax):
                self.a = self.acceleration * sign

        #Change in direction
        if sign != v_sign:
            self.a = self.acceleration * sign

    #check if already at max speed
        if abs(self.v) > abs(self._vmax):
            if sign == v_sign:
                self.v = self._vmax * v_sign
                self.a = 0

        self.v = ephem.degrees(self.v + self.a * self.timestep)
        steps = self.v * self.timestep + self.a * (
            self.timestep * self.timestep) / 2
        self.beta = self.beta + steps
        return steps

    def doSteps(self, steps):
        #sleep
        time.sleep(self.timesleep)
        if self.log:
            self.saveDebug(steps, 0)

    def saveDebug(self, steps, motorBeta):
        line="%g %g %g %g %g %g %g %g %g %g\r\n" % (time.time()-self.T0,self.timestep, \
         self.timesleep,self._vmax,self.beta_target,self.beta,self.v,self.a,motorBeta,steps)
        self.logfile.write(line)

