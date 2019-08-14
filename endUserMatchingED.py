from __future__ import division
import os
import numpy as np
import cv2
from wand.image import Image
from skimage.measure import compare_ssim
import pdftotext
import glob
import json
import re
import fitz
from utils import preProcessPdf,initCONFIG,decorationPrint,fixSpaceColonString
from difflib import SequenceMatcher
from PyPDF2 import PdfFileWriter, PdfFileReader
import io
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red
from reportlab.lib.pagesizes import letter
from shutil import copyfile,rmtree
from bs4 import BeautifulSoup

def findFontSize(file,key):
	os.system('pdf2txt.py -o output.html -t html \''+file+'\'')
	htmlData = open('output.html', 'r')
	soup = BeautifulSoup(htmlData)
	font_spans = [ data for data in soup.select('span') if 'font-size' in str(data) ]
	output = []
	for i in font_spans:
		tup = ()
		fonts_size = re.search(r'(?is)(font-size:)(.*?)(px)',str(i.get('style'))).group(2)
		tup = (str(i.text).strip(),fonts_size.strip())
		output.append(tup)

	targetSize=14
	for out in output:
		if (out[0].find(key)!=-1):
			targetSize=int(out[1])
			break
	return targetSize

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

def fixScript(lineList):
	l=len(lineList)
	for i in range(l): lineList[i]=fixSpaceColonString(lineList[i])
	return lineList

def getPDFSize(file):
	doc=PdfFileReader(open(file,'rb'))
	box=doc.getPage(0).mediaBox
	width=box[2]
	height=box[3]
	return width,height

def drawTextboxMissingKws(sourceFile,modifiedFile,key,configString,s,CONFIG):
	doc=fitz.open(sourceFile)
	l=len(configString)
	
	# Search for first column in pdf
	tmpPage=doc[0]
	startColumn=tmpPage.searchFor(s[0])[0][0]

	for page in doc:
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

def triggerWarning(path,file,template,configString,s,CONFIG,lineList):
	# Find missing keywords
	missingKws=[key for key in configString if key not in s]

	# Examine if the order of keywords is caused damaged
	keywordRank={}
	mishandledKws=[]
	checked={}
	l=len(s)
	for key in configString: 
		keywordRank[key]=configString.index(key)
		checked[key]=0
	for key in s:
		if (checked[key]): continue
		i=s.index(key)
		for j in range(i+1,l-1):
			checkedKey=s[j]
			if (keywordRank[key]>keywordRank[checkedKey]):
				mishandledKws.append(key)
				mishandledKws.append(checkedKey)
				checked[key]=checked[checkedKey]=1
				break

	lenLineList=len(lineList)
	# import pdb
	# pdb.set_trace()
	if (not (len(missingKws) or len(mishandledKws))): return
	startFilenamePos=len(path)
	modifiedFile=path+'/warning'+file[startFilenamePos:]
	copyfile(file,modifiedFile)
	sourceFolder=path+'/mummy'
	sourceFile=sourceFolder+file[startFilenamePos:]
	copyfile(file,sourceFile)
	if (len(missingKws)):
		for key in missingKws:
			drawTextboxMissingKws(sourceFile,modifiedFile,key,configString,s,CONFIG)
	if (len(mishandledKws)):
		count={}
		for key in mishandledKws: count[key]=0

		for i in range(lenLineList):
			for key in mishandledKws:
				if (lineList[i].find(key)!=-1): count[key]+=1

		for key in mishandledKws: 
			drawTextboxMishandled(key,sourceFile,modifiedFile,count,CONFIG)

def createListOfStringLineList(CONFIG,lineList,configString):
	l=len(lineList)
	checked={}
	ansList=[[configString[0]]]
	for key in CONFIG: checked[key]=0
	checked[configString[0]]=1

	for i in range(l):
		posDict={}
		posList=[]
		for key in CONFIG:
			pos=lineList[i].find(key)
			if (pos!=-1): 
				posDict[key]=pos
				posList.append(key)
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
					tmpDis=getEditDistance(ans,tmpConfig)
					if (tmpDis<minDis):
						minDis=tmpDis
						chosenAns=ans
				tmp=chosenAns.copy()
				tmp.remove(key)
				tmp.append(key)
				ansList.append(tmp)
	return ansList

def findTemplateBetaVersion(path,file,jsonDir):
	jsonFiles=glob.glob(jsonDir)
	minDistance=100000
	for jsonFile in jsonFiles:
		CONFIG,HF_CONFIG=initCONFIG(jsonFile)
		lineList=preProcessPdf(file)
		lineList=fixScript(lineList)
		for key in CONFIG: key=fixSpaceColonString(key)
		configString=createStringList(CONFIG)

		sList=createListOfStringLineList(CONFIG,lineList,configString)
		for s in sList:
			dis=getEditDistance(configString,s)
			if (minDistance>dis): 
				minDistance=dis
				ans=jsonFile[9:-5]
				targetConfigString=configString
				targetS=s
				targetCONFIG=CONFIG
	if (minDistance>5): return -1,-1
	if (minDistance!=0): 	
		triggerWarning(path,file,ans,targetConfigString,targetS,targetCONFIG,lineList)
	return ans,minDistance

def endUserSolve(resultFile,path,matchingFolder,jsonDir):
	matchingFiles=glob.glob(matchingFolder)
	for file in matchingFiles:
		decorationPrint(resultFile,'-',36)
		ans,minDistance=findTemplateBetaVersion(path,file,jsonDir)
		if (ans==-1): resultFile.write(file[9:]+' unknown template\n')
		else:
			pos=re.search(path+'/',file).span()
			resultFile.write(file[pos[1]:]+' '+ans+'\n')
			if (minDistance!=0): resultFile.write('Warning: '+file[pos[1]:]+' doesn\'t fully match the template\n')
		decorationPrint(resultFile,'-',36)

def templateMatch(path,jsonDir):
	with open(path+'/result.txt','w',encoding='utf8') as resultFile:
		if os.path.isdir(path+'/'+'warning'):
			files=glob.glob(path+'/'+'warning/*pdf') 
			for file in files: os.remove(file)
			os.rmdir(path+'/'+'warning')
		if os.path.isdir(path+'/'+'mummy'): 
			files=glob.glob(path+'/'+'mummy/*pdf') 
			for file in files: os.remove(file)
			os.rmdir(path+'/'+'mummy')
		os.makedirs(path+'/'+'warning')
		os.makedirs(path+'/'+'mummy')
		exactPath=path+'/*pdf'
		decorationPrint(resultFile,'#',50)
		resultFile.write('RANDOM TESTING\n')
		endUserSolve(resultFile,path,exactPath,jsonDir)
		decorationPrint(resultFile,'#',50)
		rmtree(path+'/mummy')

def main():
	jsonDir='template/*json'
	templateMatch('matching/random',jsonDir)
	
if __name__=='__main__': main()