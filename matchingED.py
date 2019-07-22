from __future__ import division
import os
import numpy as np
import cv2
from wand.image import Image
from skimage.measure import compare_ssim
import pdftotext
import glob
import json
from utils import preProcessPdf,initCONFIG
from difflib import SequenceMatcher

def createStringLineList(CONFIG,lineList):
	l=len(lineList)
	s=[]
	checked={}
	for key in CONFIG: checked[key]=0
	for i in range(l):
		for key in CONFIG:
			if (not checked[key]):
				barPos=key.find('_')
				if (barPos!=-1): realKey=key[:barPos]
				else: realKey=key 
				if (lineList[i].find(realKey)!=-1): 
					s.append(key)
					checked[key]=1
	return s

def createStringList(CONFIG):
	s=[]
	for key in CONFIG: s.append(key)
	return s

def getEditDistance(s0,s1):
	l0=len(s0)
	l1=len(s1)
	dp=[[0 for j in range(l1+1)] for i in range(l0+1)]

	for i in range(l0+1):
		for j in range(l1+1):
			if (i==0): dp[i][j]=j
			elif (j==0): dp[i][j]=i
			elif (s0[i-1]==s1[j-1]): dp[i][j]=dp[i-1][j-1]
			else: dp[i][j]=1+min({dp[i-1][j],dp[i][j-1],dp[i-1][j-1]}) 
	return dp[l0][l1]

def findTemplate(file,jsonDir):
	jsonFiles=glob.glob(jsonDir)
	minDistance=100000
	lineList=preProcessPdf(file)
	for jsonFile in jsonFiles:
		CONFIG=initCONFIG(jsonFile)
		configString=createStringList(CONFIG)
		s1=createStringLineList(CONFIG,lineList)
		dis=getEditDistance(configString,s1)
		if (minDistance>dis): 
			minDistance=dis
			ans=jsonFile[9:-5]
	if (minDistance>5): ans=-1
	return ans
			
def solve(matchingFolder,jsonDir):
	matchingFiles=glob.glob(matchingFolder)
	for file in matchingFiles:
		ans=findTemplate(file,jsonDir)
		if (ans==-1): print(file[9:],'unknown template')
		else: print(file[9:],ans)

def main():
	matchingFolder='matching/*pdf'
	jsonDir='template/*json'
	solve(matchingFolder,jsonDir)

if __name__=='__main__': main()
