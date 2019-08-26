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
from utils import *
from difflib import SequenceMatcher
from PyPDF2 import PdfFileWriter, PdfFileReader
import io
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red
from reportlab.lib.pagesizes import letter
from shutil import copyfile,rmtree
from bs4 import BeautifulSoup

def triggerWarning(inputPath,resultPath,file,template,configString,s,CONFIG,lineList,ans,standardFolder,CURR_KW,aliasDict,newKwList):
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
		for j in range(i+1,l):
			checkedKey=s[j]
			if (keywordRank[key]>keywordRank[checkedKey]):
				if key not in mishandledKws: mishandledKws.append(key)
				if checkedKey not in mishandledKws: mishandledKws.append(checkedKey)
				checked[key]=checked[checkedKey]=1
				break
	lenLineList=len(lineList)

	# # New keys
	# newKwList=generateListNewKws(file,ans,CURR_KW)
	# for key in newKwList:
	# 	for tmpKey in aliasDict:
	# 		if key in aliasDict[tmpKey]: 
	# 			newKwList.remove(key)
	# 			break
	# print(missingKws)
	# print(mishandledKws)
	if (not (len(missingKws) or len(mishandledKws) or len(newKwList))): return


	doc=fitz.open(file)
	page=doc[0]
	if (not len(page.searchFor(configString[0]))): missingKws.append(configString[0])

	startFilenamePos=len(inputPath)
	modifiedFile=resultPath+'/warning'+file[startFilenamePos:]
	copyfile(file,modifiedFile)
	sourceFolder=resultPath+'/mummy'
	sourceFile=sourceFolder+file[startFilenamePos:]
	copyfile(file,sourceFile)
	if (len(missingKws)):
		for key in missingKws:
			drawTextboxMissingKws(sourceFile,modifiedFile,key,configString,s,CONFIG,ans,standardFolder)
	if (len(mishandledKws)):
		count={}
		for key in mishandledKws: count[key]=0

		for i in range(lenLineList):
			for key in mishandledKws:
				if (lineList[i].find(key)!=-1): count[key]+=1

		for key in mishandledKws: 
			drawTextboxMishandled(key,sourceFile,modifiedFile,count,CONFIG)
	if (len(newKwList)):
		for key in newKwList: 
			drawTextboxNewKws(key,sourceFile,modifiedFile,CONFIG)

def findTemplateBetaVersion(inputPath,resultPath,file,jsonDir,standardFolder,CURR_KW):
	jsonFiles=glob.glob(jsonDir)
	minDistance=100000
	starPos=jsonDir.find('*')
	for jsonFile in jsonFiles:
		CONFIG,HF_CONFIG=initCONFIG(jsonFile) # HF_CONFIG for fun
		lineList=preProcessPdf(file)
		lineList=fixScript(lineList)
		for key in CONFIG: key=fixSpaceColonString(key)
		configString=createStringList(CONFIG)
		sList,aliasDict=createListOfStringLineList(CONFIG,lineList,configString)
		# New keys
		newKwList=generateListNewKws(file,jsonFile[starPos:-5],CURR_KW,jsonDir)
		for key in newKwList:
			for tmpKey in aliasDict:
				found=0
				for element in aliasDict[tmpKey]:
					if element.find(key)!=-1: 
						newKwList.remove(key)
						found=1
						break
				if (found): break
		for s in sList:
			dis=getDamerauDistance(configString,s,aliasDict)
			dis+=len(newKwList)*0.5

			# Testing===========================================================================
			# print('=========================================================================')
			# print('Standard string:',configString)
			# print('Target S:',s)
			# print('Distance:',dis)
			# print('Template:',jsonFile[starPos:-5])
			# print('=========================================================================')
			# Testing==========================================================================

			if (minDistance>dis): 
				minDistance=dis
				ans=jsonFile[starPos:-5]
				targetConfigString=configString
				targetS=s
				targetCONFIG=CONFIG
				targetAliasDict=aliasDict
				targetNewKwList=newKwList

				# Testing===========================================================================
				print('=========================================================================')
				print('Standard string:',configString)
				print('Target S:',s)
				print('Distance:',minDistance)
				print('Template:',jsonFile[starPos:-5])
				print('=========================================================================')
				# Testing==========================================================================
	# print(file)
	if (minDistance>8): return -1,-1
	if (minDistance!=0): 	
		triggerWarning(inputPath,resultPath,file,ans,targetConfigString,targetS,targetCONFIG,lineList,ans,standardFolder,CURR_KW,targetAliasDict,targetNewKwList)
	return ans,minDistance

def endUserSolve(resultFile,inputPath,resultPath,matchingFolder,jsonDir,standardFolder):
	matchingFiles=glob.glob(matchingFolder)
	CURR_KW={}
	for file in matchingFiles:
		decorationPrint(resultFile,'-',36)
		ans,minDistance=findTemplateBetaVersion(inputPath,resultPath,file,jsonDir,standardFolder,CURR_KW)
		if (ans==-1):
			pos=re.search(inputPath+'/',file).span()
			resultFile.write(file[pos[1]:]+' unknown template\n')
		else:
			pos=re.search(inputPath+'/',file).span()
			resultFile.write(file[pos[1]:]+' '+ans+'\n')
			if (minDistance!=0): resultFile.write('Warning: '+file[pos[1]:]+' doesn\'t fully match the template\n')

			# New key===============================================
			# resultFile.write('New keywords: ')
			# for key in generateListNewKws(file,ans,CURR_KW): resultFile.write(key+'\n')
			# resultFile.write('\n')
			# ======================================================
		decorationPrint(resultFile,'-',36)

def templateMatch(inputPath,resultPath,jsonDir,standardFolder):
	with open(resultPath+'/result.txt','w',encoding='utf8') as resultFile:
		if os.path.isdir(resultPath+'/'+'warning'):
			files=glob.glob(resultPath+'/'+'warning/*pdf') 
			for file in files: os.remove(file)
			os.rmdir(resultPath+'/'+'warning')
		if os.path.isdir(resultPath+'/'+'mummy'): 
			files=glob.glob(resultPath+'/'+'mummy/*pdf') 
			for file in files: os.remove(file)
			os.rmdir(resultPath+'/'+'mummy')
		os.makedirs(resultPath+'/'+'warning')
		os.makedirs(resultPath+'/'+'mummy')
		matchingPath=inputPath+'/*pdf'
		decorationPrint(resultFile,'#',50)
		resultFile.write('MATCHING\n')
		endUserSolve(resultFile,inputPath,resultPath,matchingPath,jsonDir,standardFolder)
		decorationPrint(resultFile,'#',50)
		rmtree(resultPath+'/mummy')

def main():
	jsonDir='../template/*json'
	standardFolder='../sample/'
	inputPath='../matching/random'
	resultPath='../result'
	templateMatch(inputPath,resultPath,jsonDir,standardFolder)
	
if __name__=='__main__': main()