#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
#
# termiteOS
# Copyright (c) July 2018 Nacho Mas
'''
TLEtracker
'''
from __future__ import print_function
import zmq
import time,datetime
import ephem
import json
import logging
import math
from termiteOS.config import *
import termiteOS.nodeSkull as nodeSkull
import termiteOS.astronomy.tle as tle


class TLEtracker(nodeSkull.node):
        def __init__(self, name, port, parent_host, parent_port):
                super(TLEtracker, self).__init__(name, 'TLEtracker', port, parent_host, parent_port)
		CMDs={ 
		"follow": self.cmd_follow  \
		}
                self.addCMDs(CMDs)
		self.register()
		self.timestep=0.1
		self.gearInit()
		self.observerInit()
		self.TLEs=tle.TLEhandler()
                self.follow='none'
		self.a=0
		self.go2rise=False


	def cmd_follow(self,arg):
                sat=arg
                if not self.TLEs.TLE(sat):
                        self.follow='none'
                        return 1
                else:
                        self.follow=sat
                        return 0


	def observerInit(self):
		self.ParentCmdSocket.send('@getObserver')
		reply=json.loads(self.ParentCmdSocket.recv())
		self.observer=ephem.Observer()
		self.observer.lat=ephem.degrees(str(reply['lat']))
		self.observer.lon=ephem.degrees(str(reply['lon']))
		self.observer.horizon=ephem.degrees(str(reply['horizon']))
		self.observer.elev=reply['elev']
		self.observer.temp=reply['temp']
		self.observer.compute_pressure()


	def gearInit(self):
		self.ParentCmdSocket.send('@getGear')
                reply=self.ParentCmdSocket.recv()
                logging.info(reply)
		reply=json.loads(reply)
		self.pointError=ephem.degrees(str(reply['pointError']))
		logging.info(self.pointError)

		

	def trackSatellite(self,sat):
		error=self.pointError
		satRA,satDEC = self.satPosition(sat)
		vsatRA,vsatDEC = self.satSpeed(sat)
		self.sendTrackSpeed(vsatRA,vsatDEC)
		errorRA=ephem.degrees(abs(satRA-self.RA))
		errorDEC=ephem.degrees(abs(satDEC-self.DEC))
		if abs(errorRA)>=error or abs(errorDEC)>=error:
			logging.debug("Too much error. Slewing Errors RA:%f DEC:%f %s",errorRA,errorDEC,str(error))
			self.sendSlew(satRA,satDEC)
		else:
			pass
			logging.debug("OK. Errors RA:%f DEC:%f %s",(errorRA),(errorDEC),str(error))

	def circle(self,re,dec,r,v):
		#not finished
		self.a=v*self.timestep+self.a
		vRA=r*math.sin(self.a)
		vDEC=r*math.cos(self.a)
		self.sendTrackSpeed(vRA,vDEC)


	def sendSlew(self,RA,DEC):
		self.ParentCmdSocket.send(':Sr '+str(RA))
		reply=self.ParentCmdSocket.recv()
		self.ParentCmdSocket.send(':Sd '+str(DEC))
		reply=self.ParentCmdSocket.recv()
		self.ParentCmdSocket.send(':MS')
		reply=self.ParentCmdSocket.recv()

	def sendTrackSpeed(self,vRA,vDEC):
		self.ParentCmdSocket.send('@setTrackSpeed '+str(vRA)+' '+str(vDEC))
		reply=self.ParentCmdSocket.recv()




	def run(self):
		while self.RUN:
			time.sleep(self.timestep)
			#self.values=self.lastValue()19963
			#Call to the RA/DEC primitives for accuracy
			self.ParentCmdSocket.send('@getRA')
			self.RA=ephem.hours(self.ParentCmdSocket.recv())
			self.ParentCmdSocket.send('@getDEC')
			self.DEC=ephem.degrees(self.ParentCmdSocket.recv())
                        if not self.follow == 'none':
        			self.trackSatellite(self.follow)


	def satPosition(self,sat):
			observer=self.observer
			s=self.TLEs.TLE(sat)
			observer.date=ephem.Date(datetime.datetime.utcnow())
			s.compute(observer)
			ra,dec=(s.ra,s.dec)
			if engine['overhorizon'] and s.alt<0:
				if engine['go2rising']:
					info=observer.next_pass(s)
					ra,dec=observer.radec_of(info[1],observer.horizon)			
					logging.info("Next pass %s %f %f",info,ra,dec)
				else:
					ra,dec=(self.RA,self.DEC)
			return ra,dec


	def satSpeed(self,sat):
			seconds=self.timestep
			observer=self.observer
			s=self.TLEs.TLE(sat)
			observer.date=ephem.Date(datetime.datetime.utcnow())
			s.compute(observer)
			RA0=s.ra
			DEC0=s.dec
			observer.date=observer.date+ephem.second*seconds
			s.compute(observer)
			RA1=s.ra
			DEC1=s.dec
			vRA=ephem.degrees((RA1-RA0)/seconds-ephem.hours('00:00:01'))
			vDEC=ephem.degrees((DEC1-DEC0)/seconds)
			if engine['overhorizon'] and s.alt<0:
				vRA,vDEC=(0,0)
  			return (vRA,vDEC)

def runTLEtracker(name, port, parent_host='', parent_port=False):
    s = TLEtracker(name, port, parent_host, parent_port)
    try:
        s.run()
    except:
        s.end()

if __name__ == '__main__':
        runTLEtracker('TLEtracker0',5002,'localhost',5000)
	

