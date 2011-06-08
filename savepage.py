
import sys
import codecs
from htmlelem import GetHTMLElements
from urlparse import urlparse
from urllib import urlopen
from struct import unpack

# Given a absolute path (absurl) return the absolute version of a 
# relative path 'relurl'.
def RelToAbsPath(relurl, absurl):
	final = relurl
	if final.find("http") == -1:
		urlobj = urlparse(absurl)
		pathend = urlobj.path.rfind("/")
		if pathend == -1: pathend = len(urlobj.path)

		# If the relative url begins with a '/' (e.g. /home/images/test.jpg) this
		# path is relative to the host name.
		if relurl[0] == "/":
			final = "http://"+urlobj.netloc+"/"+relurl

		# Any other relative url is relative to the hostname and absolute url
		# path.
		else:
			final = "http://"+urlobj.netloc+"/"+urlobj.path[:pathend]+"/"+relurl
		
	return final

# Return the extension of a file prefixed with full stop (e.g. ".jpg").
def GetExt(path):
	pos = path.rfind(".")
	if pos == -1: pos = len(path)

	ext = path[pos:]
	if (ext in {".jpg":"", ".gif":"", ".jpeg":"", ".png":"", ".css":"", ".js":""}) == False:	
		return ""

	return ext

# The dictionary 'allLinks' will track all links that have been downloaded or queued to download
# along with the corresponding local path name. This prevents duplicate files being download.

allLinks = {} # = dict[absurl, localpath]

filecount = 0

# Handle Functions:
#	These are functions used to process a particular type of content,
#	extracting any further links that need to be downloaded. 
#
#	The handle function has two parameters: a byte array of data and 
#	the url that this data came from. 
#	
#	Each handle will return a tuple containing a modified version of 
#	the data to be saved (as a bytearray) to disc and a list of urls 
#	to be added to the download queue (type[absurl, localpath, handle]).

def HandleHTML(data, dataurl):
	global filecount
	global allLinks

	html = data.decode("utf-8", "strict")
	allelements = GetHTMLElements(html)[1]

	links = []		# = list[tuple[absurl, localpath, process]]
	replaced = {}	# = dict[relurl, local]

	def AddHTMLLink(absurl, relurl, localpath, process):
		if (absurl in allLinks) == False:
			allLinks[absurl] = localpath
			links.append((absurl, localpath, process))

		if (absurl in replaced) == False:
			replaced[relurl] = localpath

	if "img" in allelements:
		for e in allelements["img"]:
			if ("src" in e.attr) == False: continue

			relurl = e.attr["src"]
			absurl = RelToAbsPath(relurl, dataurl)

			localpath = "imgh"+str(filecount)+GetExt(absurl)
			filecount = filecount + 1

			AddHTMLLink(absurl, relurl, localpath, HandleRaw)

	if "link" in allelements:
		for e in allelements["link"]:
			if ("href" in e.attr) == False: continue
			if ("rel" in e.attr) == False: continue
			if e.attr["rel"] != "stylesheet": continue

			relurl = e.attr["href"]
			absurl = RelToAbsPath(relurl, dataurl)

			localpath = "css"+str(filecount)+".css"
			filecount = filecount + 1

			AddHTMLLink(absurl, relurl, localpath, HandleCSS)

	if "script" in allelements:
		for e in allelements["script"]:
			if ("src" in e.attr) == False: continue

			relurl = e.attr["src"]
			absurl = RelToAbsPath(relurl, dataurl)

			localpath = "script"+str(filecount)+".js"
			filecount = filecount + 1

			AddHTMLLink(absurl, relurl, localpath, HandleRaw)

	# Process any embedded CSS.
	if "style" in allelements:
		for e in allelements["style"]:
			stylevalue = e.children[0].value
			resultHandle = HandleCSS(stylevalue, dataurl)
			links = links + resultHandle[1]
			replaced[stylevalue] = resultHandle[0]

	# Replace all links in the page and save it to disk.
	for r in replaced.keys():
		html = html.replace(r, replaced[r])

	return (html, links)

def HandleRaw(data, dataurl):
	return (data, [])

def HandleCSS(data, dataurl):
	global filecount
	global allLinks

	css = data.decode("utf-8", "strict")

	links = []		# = list[tuple[absurl, localpath, process]]
	replaced = {}	# = dict[relurl, local]

	# Find all instances of the url() attribute in the 
	# CSS file and store the link in the database.
	# It's assumed that all url() attributes are pointing
	# to images!
	end = 0
	start = css.find("url(", end)
	while start != 0:
		end = css.find(")", start)
		if end == -1: break

		relurl = css[start+4:end].strip("\'\"")
		absurl = RelToAbsPath(relurl, dataurl)

		localpath = "imgcss"+str(filecount)+GetExt(relurl)
		filecount = filecount + 1

		if (absurl in allLinks) == False:
			allLinks[absurl] = localpath
			links.append((absurl, localpath, HandleRaw))

		if (absurl in replaced) == False:
			replaced[relurl] = localpath

		start = css.find("url(", end)

	# Replace all links in the css file and save it to disk.
	for r in replaced.keys():
		css = css.replace(r, replaced[r])

	return (css, links)

def ShowUsage():
	print "Usage: savepage.py <url> <outpath>"

# Get the command line parameters.
if len(sys.argv) < 3:
	ShowUsage()
	sys.exit("ERROR: Not enough command line parameters provided!")

URL_HTML = sys.argv[1]
LOCAL_PATH = sys.argv[2]

# urllib requries the http:// prefix.
if URL_HTML.find("http://") == -1: URL_HTML = "http://"+URL_HTML

# A queue of all links to be downloaded and processed. Start with the source HTML page.

queue = []	# list[tuple[absurl, localpath, handle]]

queue.append((URL_HTML, "main.html", HandleHTML))

while len(queue) > 0:
	item = queue[0]

	print "Downloading "+item[0],
	try:
		handle = urlopen(item[0])
		data = handle.read()
		handle.close()
		print "OK!"

		# Call the file's handle. Returns the data with modified links
		# and a list of new links to add to the queue.
		handleResult = item[2](data, item[0])

		# Save the modified byte array to disc.
		try:
			filename = LOCAL_PATH+"\\"+item[1]
			print "Saving " + filename
			f = open(filename, "wb")
			f.write(handleResult[0])
			f.close()
			print "OK!"
		except IOError:
			print "DISC FAIL!"

		# Add any new links to the queue.
		queue = queue + handleResult[1]
	except IOError:
		print "URL FAIL!"

	queue = queue[1:]

