#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
#
# termiteOS
# Copyright (c) July 2018 Nacho Mas

from __future__ import print_function
from __future__ import with_statement

import sys
import yaml
import termiteOS.nodes.hub as hub
import os
status=True


def run_in_separate_process(func, *args, **kwds):
	pid = os.fork()
	if pid > 0:
		status=True
    	else: 
        	try:
        	    result = func(*args, **kwds)
        	    status = True
        	except Exception, exc:
			result = exc
			status = False
			print("FAIL:",result)
		#os._exit(status)
	return status



def launchnode(nodedict,parent_host='',parent_port=False):
	global status
	name=nodedict.keys()[0]
	elements=nodedict[name]
	nodetype=elements['type']
	host=elements['host']
	port=elements['port']
	print("Launching node:"+name+ " type:",nodetype)
	print("--> Host:",host,"Port:",port,"Parent Host:",parent_host,"Parent Port:",parent_port)
	status= status and run_in_separate_process(hub.runhub,name,port,parent_host,parent_port)
	if 'nodes' in elements.keys():
		print("--> Module:",name," has chidrens. Launching..")
		for node in elements['nodes']:
			status=status and launchnode(node,host,port)
	return status



	

def launchmachine(yamlfile):
	with open(yamlfile) as y:
		doc=y.read()
		print(doc)
	try:
		ydoc=yaml.load(doc)
	except:
		print("Launch:malformed yaml \n"+doc)
	#print(ydoc)
	return launchnode(ydoc)
	


if __name__ == '__main__':
 	if len(sys.argv)!=2:
		print("usage:"+sys.argv[0]+" yaml_file")
		exit(1)
	yamlfile=sys.argv[1]
 	print("Reading from:"+yamlfile)
	print(launchmachine(yamlfile))
	
