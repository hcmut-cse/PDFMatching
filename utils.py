from __future__ import division
import os
import numpy as np
import cv2
from wand.image import Image
from bs4 import BeautifulSoup
import pandas as pd
from skimage.measure import compare_ssim
import pdftotext
import glob
import json
import fitz
import re
from difflib import SequenceMatcher
from shutil import copyfile,rmtree

def remove_at(s, i):
	return s[:i] + s[i+1:]

def preProcessPdf(filename):
	# for filename in file:
	# Covert PDF to string by page
	# print(filename)
	with open(filename, "rb") as f:
		pdf = pdftotext.PDF(f)
	# Remove header & footer
	# print(len(pdf))
	if (len(pdf) > 1):
		# fullPdf = removeHeaderAndFooter(pdf)
		fullPdf = []
		for i in range(len(pdf)):
			if (pdf[i].strip() != ''):
				fullPdf.append(pdf[i].split('\n'))
		# Join PDF
		fullPdf = [line for page in fullPdf for line in page]
	else:
		fullPdf = pdf[0].split('\n')
	for page in fullPdf:
		i=fullPdf.index(page)
		fullPdf[i]=re.sub(r'^( )*[0-9]$','',fullPdf[i])

	# for page in fullPdf: print(page)
	return fullPdf

def initCONFIG(jsonFile):
	with open(jsonFile,'r',encoding='utf8') as json_file: ORIGINAL_CONFIG=json.load(json_file)
	CONFIG=ORIGINAL_CONFIG[0].copy()
	HF_CONFIG=ORIGINAL_CONFIG[1].copy()
	return CONFIG,HF_CONFIG

def decorationPrint(file,c,times):
	for i in range(times): file.write(c)
	file.write('\n')

def fixSpaceColonString(line):
	ans=re.sub(r'( )+:',' :',line)
	return ans

def createStringList(CONFIG):
	s=[]
	checked={}
	for key in CONFIG:
		tmpKey=key 
		barPos=key.find('_')
		if (barPos!=-1):
			tmpKey=key[:barPos]
		checked[tmpKey]=0

	for key in CONFIG: 
		tmpKey=key
		if (key.find('_')!=-1): 
			barPos=key.find('_')
			tmpKey=key[:barPos]
		if (not checked[tmpKey]): 
			s.append(tmpKey)
			checked[tmpKey]=1
	return s

def investigateAnalogy(a,b,aliasDict):
	if (a==b): return 1
	if (a.lower() in aliasDict[b]): return 1
	if (b.lower() in aliasDict[a]): return 1
	return 0

def getEditDistance(s0,s1,aliasDict):
	l0=len(s0)
	l1=len(s1)
	dp=[[0 for j in range(l1+1)] for i in range(l0+1)]

	for i in range(l0+1):
		for j in range(l1+1):
			if (i==0): dp[i][j]=j
			elif (j==0): dp[i][j]=i
			elif (investigateAnalogy(s0[i-1],s1[j-1],aliasDict)): dp[i][j]=dp[i-1][j-1]
			else: dp[i][j]=1+min({dp[i-1][j],dp[i][j-1],dp[i-1][j-1]}) 
	return dp[l0][l1]

def getDamerauDistance(s0,s1,aliasDict):
	l0=len(s0)
	l1=len(s1)
	dp=[[0 for j in range(l1+1)] for i in range(l0+1)]

	for i in range(l0+1):
		for j in range(l1+1):
			if (i==0): dp[i][j]=j
			elif (j==0): dp[i][j]=i
			elif (investigateAnalogy(s0[i-1],s1[j-1],aliasDict)): dp[i][j]=dp[i-1][j-1]
			else: dp[i][j]=1+min({dp[i-1][j],dp[i][j-1],dp[i-1][j-1]}) 
			if (i>1 and j>1 and investigateAnalogy(s0[i-1],s1[j-2],aliasDict) and investigateAnalogy(s0[i-2],s1[j-1],aliasDict)): dp[i][j]=min(dp[i][j],dp[i-2][j-2]+1)
	return dp[l0][l1]

def fixScript(lineList):
	l=len(lineList)
	for i in range(l): lineList[i]=fixSpaceColonString(lineList[i])
	return lineList

def drawTextboxMissingKws(sourceFile,modifiedFile,key,configString,s,CONFIG,ans):
	doc=fitz.open(sourceFile)
	l=len(configString)
	# Search for first column in pdf
	tmpPage=doc[0]
	for tmpKey in s:
		if (len(tmpPage.searchFor(s[0]))): 
			startColumn=tmpPage.searchFor(s[0])[0][0]
			break
	index=0
	for page in doc:
		noApproximation=0
		# Warn based on other files
		homogeneousPdfFiles=glob.glob('matching/random/'+ans+'/*pdf')
		for file in homogeneousPdfFiles:
			tmpDoc=fitz.open(file)
			tmpPage=tmpDoc[index]
			tmpLength=len(tmpPage.searchFor(key))
			if (tmpLength):
				targetFile=file
				for pos in tmpPage.searchFor(key):
					if (key=='Collect'):
						if (len(tmpPage.searchFor('Freight Collect'))): 
							FreightCollectPos=tmpPage.searchFor('Freight Collect')[0]
							if (FreightCollectPos[1]==pos[1]): continue
						if (len(tmpPage.searchFor('Total Collect'))): 
							TotalCollectPos=tmpPage.searchFor('Total Collect')[0]
							if (TotalCollectPos[1]==pos[1]): continue
					targetPos=pos
					noApproximation=1
					break
				if (noApproximation): break
		if (noApproximation):
			x0=targetPos[0]	
			y0=targetPos[1]	
			x1=targetPos[2]+len(key)*4	
			y1=targetPos[3]+10
			rect=fitz.Rect(x0,y0,x1,y1)
			highlight=page.addFreetextAnnot(rect,key,fontsize=12, fontname="helv", color=(1, 0, 0), rotate=0)	
			break
		index+=1

	if (not noApproximation):
		for page in doc:
			# Approximation
			targetSize=findFontSize(sourceFile,key)
			i=configString.index(key)
			latestKey=configString[0]
			nextKey=configString[i]
			for j in range(i-1,0,-1):
				if (configString[j] in s): 
					latestKey=configString[j]
					break
			for j in range(i+1,l):
				if (configString[j] in s):
					nextKey=configString[j]
					break
			if (nextKey.find('_')!=-1):
				barPos=nextKey.find('_')
				nextKey=nextKey[:barPos]
			if (nextKey==key): nextKey=CONFIG[key]['endObject']['bottom']
			if (not CONFIG[latestKey]['row'][1] or not CONFIG[latestKey]['row'][0]): numLines=1
			else: numLines=CONFIG[latestKey]['row'][1]-CONFIG[latestKey]['row'][0]
			if (not CONFIG[latestKey]['column'][1] or not CONFIG[latestKey]['column'][0]): width=1
			else: width=CONFIG[latestKey]['column'][1]-CONFIG[latestKey]['column'][0]
			latest_text_instances=page.searchFor(latestKey)
			if (page.searchFor(nextKey)):
				next_inst=page.searchFor(nextKey)[0]
				if (latest_text_instances):
					for inst in latest_text_instances:
						if (inst[3]<next_inst[1]):
							x0=inst[0]
							y0=(inst[3]+targetSize*numLines)
							if (CONFIG[latestKey]['row'][0]==CONFIG[key]['row'][0]): 
								y0=inst[1]
								x0+=width*(targetSize-5)
							else: x0=startColumn
							x1=x0+len(key)*targetSize*0.7
							y1=y0+targetSize*1.4
							rect=fitz.Rect(x0,y0,x1,y1)
							highlight=page.addFreetextAnnot(rect,key,fontsize=targetSize-2, fontname="helv", color=(1, 0, 0), rotate=0)
				else:
					x0=next_inst[0]
					y0=(next_inst[1]-targetSize)
					if (nextKey in CONFIG):
						if (CONFIG[nextKey]['row'][0]==CONFIG[key]['row'][0]): 
							y0=next_inst[1]
							x0+=width*(targetSize-5)
						else: x0=startColumn
					x1=x0+len(key)*targetSize*0.7
					y1=y0+targetSize*1.4
					rect=fitz.Rect(x0,y0,x1,y1)
					highlight=page.addFreetextAnnot(rect,key,fontsize=targetSize-2, fontname="helv", color=(1, 0, 0), rotate=0)
	doc.save(modifiedFile,garbage=4,deflate=True,clean=False)
	copyfile(modifiedFile,sourceFile)

def drawTextboxMishandled(key,sourceFile,modifiedFile,count,CONFIG):
	doc=fitz.open(sourceFile)
	for page in doc:
		text_instances=page.searchFor(key)
		for inst in text_instances: 
			trueInst=1
			if (count[key]>1):
				for margin in CONFIG[key]['endObject']:
					tmpKey=CONFIG[key]['endObject'][margin]
					if (tmpKey=='same_left'): tmpKey=CONFIG[key]['endObject']['left']
					if (tmpKey!=-1):
						if (margin=='top'):
							if (page.searchFor(tmpKey)):
								tmpPos=page.searchFor(tmpKey)[0]
								if (tmpPos[1]>inst[3]): 
									trueInst=0
									break
						elif (margin=='bottom'):
							if (page.searchFor(tmpKey)):
								tmpPos=page.searchFor(tmpKey)[0]
								if (tmpPos[3]<inst[1]):
									trueInst=0
									break
						elif (margin=='left'):
							if (page.searchFor(tmpKey)):
								tmpPos=page.searchFor(tmpKey)[0]
								if (tmpPos[0]>inst[2]):
									trueInst=0
									break
						else:
							if (page.searchFor(tmpKey)):
								tmpPos=page.searchFor(tmpKey)[0]
								if (tmpPos[2]<inst[0]):
									trueInst=0
									break
									
			if (trueInst):
				highlight=page.addHighlightAnnot(inst)
				highlight.setColors({"stroke": (0,1,0)})
				break
					
	doc.save(modifiedFile,garbage=4, deflate=True, clean=False)
	copyfile(modifiedFile,sourceFile)

def createListOfStringLineList(CONFIG,lineList,configString):
	l=len(lineList)
	checked={}
	ansList=[[configString[0]]]
	for key in CONFIG: checked[key]=0
	checked[configString[0]]=1
	aliasDict={}
	for key in CONFIG:
		aliasDict[key]=[]
		if ('alias' in CONFIG[key]):
			for alias in CONFIG[key]['alias']:
				aliasName=CONFIG[key]['alias'][alias]['name']
				aliasDict[key].append(aliasName)
	for i in range(l):
		posDict={}
		posList=[]
		for key in CONFIG:
			pos=lineList[i].find(key)
			if (pos!=-1):
				posDict[key]=pos
				posList.append(key)
			for alias in aliasDict[key]:
				pos=lineList[i].find(alias)
				if (pos!=-1):
					posDict[key]=pos
					posList.append(key)
					break
		posDict=dict(sorted(posDict.items(),key=lambda k:k[1]))
		for key in posDict: 
			if not (checked[key]):
				for s in ansList: s.append(key)
				checked[key]=1
			else:
				minDis=10000000000
				for ans in ansList:
					numWords=len(ansList[0])
					tmpConfig=configString[:numWords]
					tmpDis=getEditDistance(ans,tmpConfig,aliasDict)
					if (tmpDis<minDis):
						minDis=tmpDis
						chosenAns=ans
				tmp=chosenAns.copy()
				tmp.remove(key)
				tmp.append(key)
				ansList.append(tmp)
	return ansList,aliasDict