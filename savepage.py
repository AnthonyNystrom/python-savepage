
import sys
import codecs
from urlparse import urlparse
from urllib import urlopen
from struct import unpack

# An object representing an html element, containing a name and
# a dictionary of attributes. Constructed from a sub-string of a string
# representing the HTML content.
class HTMLElement:
	def __init__(self, elem):
		endname = elem.find(" ")
		if endname == -1: endname = len(elem)

		self.name = elem[:endname]
		self.attr = {}
		self.children = []

		RemoveChar = lambda x: x.strip("\ \n\r\t\"=")

		# Extrct attributes from the element by partitioning
		# the string around the '=' character (left of this character
		# is the key and to the right is the value).
		parts = ('a','a',elem[endname:])
		while parts[2].find("=") != -1:
			parts = parts[2].partition("=")
			key = RemoveChar(parts[0])

			# If the right hand partition is empty there exists
			# an attribute at the end of an element that has no value.
			if len(parts[2]) == 0: break

			valsep = parts[2][0]
			parts = parts[2][1:].partition(valsep)
			value = RemoveChar(parts[0])

			self.attr[key] = value

# Return a tuple containing the start and end index inside html that
# forms a full html element (e.g. <img src='test.png'>).
def FindNextHTMLElement(html, begin):
	start = html.find("<", begin)
	if start == -1: return None
	start = start + 1

	end = html.find(">", start)
	if end == -1: return None

	return (start,end)
		
# Return a dictionary where each key is a element name in the 
# html page and the value is a list of HTMLElement objects.
# Start and end elements (<img> and </img>) are stored as 
# separate keys.
def GetHTMLElem(html):
	elements = {}
	pos = FindNextHTMLElement(html, 0)

	while pos != None:
		elem = HTMLElement(html[pos[0]:pos[1]])
		if elem.name in elements: elements[elem.name].append(elem)
		else: elements[elem.name] = [elem]

		pos = FindNextHTMLElement(html, pos[1])

	return elements

# Convert a relative path (relative to an absolute path) to an absolute path
# on the host.
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

# This dictionary will track all links that have been downloaded or queued to download
# along with the corresponding local path name. This prevents duplicate files being download.

allLinks = {} # = dict[absurl, localpath]

filecount = 0

# Given data representing an HTML page, save it to disk and extract all
# the embedded links and returning them as a list.
def ProcessHTML(data, dataurl, datalocalpath):
	global filecount
	global allLinks

	html = data.decode("utf-8", "strict")
	allelements = GetHTMLElem(html)

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

			AddHTMLLink(absurl, relurl, localpath, ProcessRaw)

	if "link" in allelements:
		for e in allelements["link"]:
			if ("href" in e.attr) == False: continue
			if ("rel" in e.attr) == False: continue
			if e.attr["rel"] != "stylesheet": continue

			relurl = e.attr["href"]
			absurl = RelToAbsPath(relurl, dataurl)

			localpath = "css"+str(filecount)+".css"
			filecount = filecount + 1

			AddHTMLLink(absurl, relurl, localpath, ProcessCSS)

	if "script" in allelements:
		for e in allelements["script"]:
			if ("src" in e.attr) == False: continue

			relurl = e.attr["src"]
			absurl = RelToAbsPath(relurl, dataurl)

			localpath = "script"+str(filecount)+".js"
			filecount = filecount + 1

			AddHTMLLink(absurl, relurl, localpath, ProcessRaw)

	# Replace all links in the page and save it to disk.
	for r in replaced.keys():
		html = html.replace(r, replaced[r])

	print "Saving " + datalocalpath,

	try:
		f = codecs.open(datalocalpath, encoding="utf-8", mode="w+")
		f.write(html)
		f.close()
		print "OK!"
	except IOError:
		print "FAIL!"

	return links

# Given some raw data downloaded through http, save it to disk.
def ProcessRaw(data, dataurl, datalocalpath):
	print "Saving " + datalocalpath,

	try:
		f = open(datalocalpath, "wb")
		f.write(data)
		f.close()
		print "OK!"
	except IOError:
		print "FAIL!"

	return []

# Given data representing a CSS file, extract all image
# attribute urls.
def ProcessCSS(data, dataurl, datalocalpath):
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

		relurl = css[start+4:end]
		absurl = RelToAbsPath(relurl, dataurl)

		localpath = "imgcss"+str(filecount)+GetExt(relurl)
		filecount = filecount + 1

		if (absurl in allLinks) == False:
			allLinks[absurl] = localpath
			links.append((absurl, localpath, ProcessRaw))

		if (absurl in replaced) == False:
			replaced[relurl] = localpath

		start = css.find("url(", end)

	# Replace all links in the css file and save it to disk.
	for r in replaced.keys():
		css = css.replace(r, replaced[r])

	print "Saving " + datalocalpath,

	try:
		f = codecs.open(datalocalpath, encoding="utf-8", mode="w+")
		f.write(css)
		f.close()
		print "OK!"
	except IOError:
		print "FAIL!"

	return links

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

queue = []	# list[tuple[absurl, localpath, process]]

queue.append((URL_HTML, "main.html", ProcessHTML))

while len(queue) > 0:
	item = queue[0]

	print "Downloading "+item[0],
	try:
		handle = urlopen(item[0])
		data = handle.read()
		handle.close()
		print "OK!"

		# Process this file, adding any new links to the queue and
		# saving the link to disk (all links in the data will be modified
		# to the local version before being saved).
		queue = queue + item[2](data, item[0], LOCAL_PATH+"\\"+item[1])
	except IOError:
		print "FAIL!"

	queue = queue[1:]

