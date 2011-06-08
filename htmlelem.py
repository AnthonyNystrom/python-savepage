
# Example DFS tree traversal:
#	from htmlelem import GetHTMLElements
#	data = GetHTMLElements(httpdata)
#	
#	stack = [data[0]]
#	while len(stack) > 0:
#		top = stack.pop()
#		for c in top.children: stack.append(c)
#		if top.name == "[Text]": print "Text: "+top.value
#		else: print "Name: "+top.name

# An object representing an html element, containing a name and
# a dictionary of attributes. Can be constructed from a sub-string 
# of a string representing the HTML content, otherwise an empty
# HTMLElement is created.
class HTMLElement:
	def __init__(self, elem = None):
		self.name = ""
		self.value = ""
		self.attr = {}
		self.children = []
		self.parent = None
		self.selfTerm = False

		# If no string is provided to construct the element an empty
		# HTMLElement is created.
		if elem == None: return

		endname = elem.find(" ")
		if endname == -1: endname = len(elem)

		RemoveChar = lambda x: x.strip("\ \n\r\t\"=")

		self.name = RemoveChar(elem[:endname])

		# Comments cannot be parsed for attributes, so early out.
		if self.name.find("!--") != -1: return

		# Determine if this is a self-terminating element.
		# In XHTML a self-terminating element is one in which the 
		# element content ends with a '/'. This doesn't apply to
		# old HTML where it was determined by element name only
		# (e.g. <br> was a valid self-terminating HTML element).
		self.selfTerm = (elem[len(elem)-1] == "/")

		selfTermElem = ["br", "img", "link", "meta"]
		for st in selfTermElem:
			if st == self.name: self.selfTerm = True

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

# Return a tuple containing the start and end index of this element,
# an instance of an HTMLElement object and a flag to indicate if this
# element terminates itself (e.g. <br />).
def FindNextHTMLElement(html, begin):
	start = html.find("<", begin)
	if start == -1: return None
	start = start + 1

	end = html.find(">", start)
	if end == -1: return None

	# If the element found is a comment, ensure that the end of the
	# element is the end of the comment and not any commented out HTML
	# elements.
	elem = html[start:end]
	if elem.find("!--") != -1:
		end = html.find("-->", start)
		end = end + 3

	return (start, end, HTMLElement(elem))
		
# Given a string containing the content of an HTML page, return a tuple
# with the root of a HTMLElement tree and a dictionary containing a 
# linked list of each HTMLElement allowing for O(1) lookup. In the 
# dictionary elements <img> and </img> appear separately.
def GetHTMLElements(html):
	# Return True if the HTMLElement 'e' is valid.
	def IsValidElem(e):
		invalid = ["!--", "!DOCTYPE"]
		for i in invalid:
			if e.name.find(i) != -1: return False
		return True

	# Set the root to the first valid HTML element.
	pos = FindNextHTMLElement(html, 0)
	while IsValidElem(pos[2]) == False and pos[2] != None:
		pos = FindNextHTMLElement(html, pos[1])

	if pos == None: return None

	# The dictionary of all HTML elements.
	elements = {}	# dict[elementName, list[HTMLElement]]

	# The HTML content is considered the result of a DFS tree traversal,
	# so to reconstruct the tree a stack is required to keep track of the
	# elements currently being traversed.
	root = pos[2]
	elemstack = [root]

	while len(elemstack) > 0:
		top = elemstack[len(elemstack)-1]

		nextPos = FindNextHTMLElement(html, pos[1])
		if nextPos == None: break

		# Extract any text that appeared between the last 
		# element snd the new element.
		text = html[pos[1]+1:nextPos[0]-1].strip()
		
		# Add text to the tree as a special HTMLElement with
		# a fixed name and using the, otherwise unused, value member.
		# The element is added as a child to the HTMLElement at
		# the top of the element stack.
		if len(text) > 0:
			textElem = HTMLElement()
			textElem.name = "[Text]"
			textElem.value = text
			textElem.parent = top
			top.children.append(textElem)

		pos = nextPos

		elem = pos[2]
		elem.parent = top

		if IsValidElem(elem):
			# Add to the elements dictionary.
			if elem.name in elements: elements[elem.name].append(elem)
			else: elements[elem.name] = [elem]

			if elem.name[0] == '/':	
				elemstack.pop()
			else: 
				top.children.append(elem)

				# Don't add self-terminating elements to the 
				# element stack.
				if elem.selfTerm == False:
					elemstack.append(elem)	

	return (root, elements)

