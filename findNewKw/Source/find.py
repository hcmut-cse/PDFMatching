from __future__ import division
import os
import json
import numpy as np
from difflib import SequenceMatcher
import pdftotext
from preprocess import preProcessPdf
from processData import extractData
from removeHeaderFooter import removeHeaderAndFooter
from removeWatermark import removeWatermark
import re
import string

CURR_KW = {}
newKw = []
def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()
# Create Dictionary of keyword for data
def countKeyword(CONFIG):
    count = 0
    for key1 in CONFIG:
        key1 = key1.lower()
        if (len(CURR_KW) == 0):
            CURR_KW[key1] = 1
        else:
            if key1 in CURR_KW:
                CURR_KW[key1] = CURR_KW[key1] + 1
            elif key1 not in CURR_KW:
                for key2 in list(CURR_KW):
                    ratio = similar(key1,key2)
                    if (ratio >= 0.85):
                        CURR_KW[key2] = CURR_KW[key2] + 1
                        break
                    else:
                        count = count + 1
                        if (count == len(CURR_KW)):
                            CURR_KW[key1] = 1
                            count = 0
# Create list keyword from other template to make data
def createData(PDF, keyword):
    for PDF_TYPE in PDF:
        #fileName = list(filter(lambda pdf: pdf[-3:] == 'pdf' ,os.listdir('../' + PDF_TYPE)))
        with open('../' + 'template' + '/' + PDF_TYPE + '.json', 'r', encoding='utf8') as json_file:
            ORIGINAL_CONFIG = json.load(json_file)
        #for file in fileName:
        # Reset Current CONFIG
        CONFIG = ORIGINAL_CONFIG[0].copy()
        HF_CONFIG = ORIGINAL_CONFIG[1].copy()
        CURR_CONFIG = {}

        # Sort CONFIG from top to bottom, from left to right
        configByColumn = dict(sorted(CONFIG.items(), key=lambda kv: kv[1]['column'][0]))
        CONFIG = dict(sorted(configByColumn.items(), key=lambda kv: kv[1]['row'][0]))

        # Create config for current pdf
        for key in CONFIG:
            CURR_CONFIG[key] = {}
            CURR_CONFIG[key]['row'] = CONFIG[key]['row'].copy()
            CURR_CONFIG[key]['column'] = CONFIG[key]['column'].copy()
        countKeyword(CURR_CONFIG)
    return HF_CONFIG
# Make data keyword for test template 
def currDataTemp(str_templateCheck, listCheck):
    with open('../' + 'template' + '/' + str_templateCheck + '.json', 'r', encoding='utf8') as json_file:
        ORIGINAL_CONFIG_CHECK = json.load(json_file)
    CONFIG_CHECK = ORIGINAL_CONFIG_CHECK[0].copy()
    # listCheck = []
    for key in CONFIG_CHECK:
        key = key.lower()
        key = re.sub(r'[0-9]+', '', key)
        key = key.replace("_","")
        listCheck.append(key)
    return listCheck
# preProcess Text to seperate word with 2 or more space
def preProcessText(listPdf, fullPdf):
    for line in fullPdf:
        line = line.lower()
        listLine = []
        listLine = re.split("\\s \\s+", line)
        listPdf.append(listLine)
    return listPdf
# Check if`keyword in data
def detectInData(fullPdf, listCheck):
    preProcessText(listPdf, fullPdf)
    for listLine in listPdf:
        for key in list(CURR_KW):
            for ele in listLine:
                ratio = similar(ele, key)
                if (ratio >= 0.8):
                    ele = ele.replace(":","")
                    ele = ele.strip()
                    if ele not in listCheck:
                        listCheck.append(ele)
                        newKw.append(ele)
                        # note = ele + " is a new keyword"
                        # print(note)
# Check if keyword first appears in current 
def detectNotInData(fullPdf, listCheck):
    # specialChar = ["!","@","#","$","%","^","&","*","(",")",":",";"]
    # kwInData = True
    # for listLine in listPdf:
    #     for ele in listLine:
    #         result = re.findall(r'[\s\w\\/\\."]+[\s]*[\\:\\#]+', ele)
    #         for i in result:
    #             if len(i) > 3:
    #                 for spec in specialChar:
    #                     if spec in i:
    #                         x = re.search(spec, i)
    #                         keyword = i[0:x.start()]
    #                         keyword = keyword.strip()
    #                         if keyword not in listCheck:
    #                             if keyword not in list(CURR_KW):
    #                                 newKw.append(keyword)


    time = 0
    specialChar = ["!","@","#","$","%","^","&","*","(",")",":",";"]
    kwInData = True
    for listLine in listPdf:
        for ele in listLine:
            t = re.findall(r'[\d]+ [\d]+:[\d]+', ele)
            
            if (len(t) > 0):
                time = t[0]
    
            result = re.findall(r'[\s\w\\/\\."]+[\s]*[\\:\\#]+', ele)
            
            for i in result:
                if len(i) > 3:
                    for spec in specialChar:
                        if spec in i:
                            x = re.search(spec, i)
                            keyword = i[0:x.start()]
                            keyword = keyword.strip()
                            if keyword not in listCheck:
                                if keyword not in list(CURR_KW):
                                    if (time != 0):
                                        if keyword not in time:
                                            newKw.append(keyword)
if __name__ == '__main__':
    
    PDF = ["1","2_6_12","3","5","7","8","9","10","11","16","17"]
    print("Input the template you want to check: ");
    template_check = input()
    str_templateCheck = str(template_check)
    
    # Data of test template
    listCheck = []
    listCheck = currDataTemp(str_templateCheck, listCheck)
    # Take keyword from others template to make data
    keyword = []
    HF_CONFIG = createData(PDF, keyword)

    fileName = list(filter(lambda pdf: pdf[-3:].lower() == 'pdf' ,os.listdir('../' + 'detectNewKey')))
    for file in fileName:
    # file = "SGNV49126500+MAIL.pdf"
	    print(file)
	    #print("----------------------------------------------------------------")
	    fullPdf, removed = preProcessPdf('../' + 'detectNewKey' + '/' + file, HF_CONFIG)
	    listPdf = []
	    detectInData(fullPdf, listCheck)
	    detectNotInData(fullPdf, listCheck)
	    print("-----------------------List new keyword of this file-------------------------")
	    with open('../' + 'detectNewKey' + '/' + file[:-3] + 'txt', 'w', encoding='utf8') as resultFile:
	        for kw in newKw:
	            resultFile.write(kw + "\n")  