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
import re
from difflib import SequenceMatcher

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


