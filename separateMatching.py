import glob
from utils import preProcessPdf,initCONFIG,decorationPrint,fixSpaceColonString,createStringList,investigateAnalogy,getEditDistance,getDamerauDistance,fixScript,drawTextboxMissingKws,drawTextboxMishandled,createListOfStringLineList

def findTemplateSeparateVersion(path,file,jsonDir):
	jsonFiles=glob.glob(jsonDir)
	minDistance=100000
	for jsonFile in jsonFiles:
		CONFIG,HF_CONFIG=initCONFIG(jsonFile) # HF_CONFIG for fun
		lineList=preProcessPdf(file)
		lineList=fixScript(lineList)
		for key in CONFIG: key=fixSpaceColonString(key)
		configString=createStringList(CONFIG)
		sList,aliasDict=createListOfStringLineList(CONFIG,lineList,configString)
		for s in sList:
			dis=getDamerauDistance(configString,s,aliasDict)
			if (minDistance>dis): 
				minDistance=dis
				ans=jsonFile[9:-5]
				targetConfigString=configString
				targetS=s
				targetCONFIG=CONFIG
		
	print(file)
	if (minDistance>5): return -1

	# ans: template
	return ans

def main():
	path='matching/random'
	jsonDir='template/*json'
	pdfFiles=glob.glob('matching/random/*pdf')
	for file in pdfFiles:
		print(file[16:],findTemplateSeparateVersion(path,file,jsonDir))

if __name__=='__main__': main()