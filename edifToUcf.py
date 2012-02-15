# edifToUcf.py
#
# based upon sexpParser.py by Paul McGuire (copyright 2007-2011)
#
# This script takes in an EDIF netlist and extracts all the nodes corresponding
# to a particular reference designator (that of the FPGA) and creates a UCF
# file. It will also assign I/O standards based upon a mapping specified near the top
# of this file. Probably in the future it would be a good idea to break that
# mapping into a separate file that can be included.
#
# Andrew 'bunnie' Huang, copyright 2012, BSD license

''' iostandardMaps is a list of tuples
    the first item in the tuple is a regex that is applied to the net name
    the second item in the tuple is the corresponding I/O standard

    Note that the programming aborts searching once the first match is found.
    Therefore, the last item should always be ".*" as the default match.
'''
iostandardMaps = [ ("^F_.*DQS_[NP]$", 'DIFF_SSTL18_II'),
                   ("F_.*CLK_[NP]$", 'DIFF_SSTL18_II'),
                   ("^F_", 'SSTL18_II'),
                   ("_[NP]$", 'TMDS_33'),
                   (".*", 'LVCMOS33') ]


"""
BNF reference: http://theory.lcs.mit.edu/~rivest/sexp.txt

<sexp>    	:: <string> | <list>
<string>   	:: <display>? <simple-string> ;
<simple-string>	:: <raw> | <token> | <base-64> | <hexadecimal> | 
		           <quoted-string> ;
<display>  	:: "[" <simple-string> "]" ;
<raw>      	:: <decimal> ":" <bytes> ;
<decimal>  	:: <decimal-digit>+ ;
		-- decimal numbers should have no unnecessary leading zeros
<bytes> 	-- any string of bytes, of the indicated length
<token>    	:: <tokenchar>+ ;
<base-64>  	:: <decimal>? "|" ( <base-64-char> | <whitespace> )* "|" ;
<hexadecimal>   :: "#" ( <hex-digit> | <white-space> )* "#" ;
<quoted-string> :: <decimal>? <quoted-string-body>  
<quoted-string-body> :: "\"" <bytes> "\""
<list>     	:: "(" ( <sexp> | <whitespace> )* ")" ;
<whitespace> 	:: <whitespace-char>* ;
<token-char>  	:: <alpha> | <decimal-digit> | <simple-punc> ;
<alpha>       	:: <upper-case> | <lower-case> | <digit> ;
<lower-case>  	:: "a" | ... | "z" ;
<upper-case>  	:: "A" | ... | "Z" ;
<decimal-digit> :: "0" | ... | "9" ;
<hex-digit>     :: <decimal-digit> | "A" | ... | "F" | "a" | ... | "f" ;
<simple-punc> 	:: "-" | "." | "/" | "_" | ":" | "*" | "+" | "=" ;
<whitespace-char> :: " " | "\t" | "\r" | "\n" ;
<base-64-char> 	:: <alpha> | <decimal-digit> | "+" | "/" | "=" ;
<null>        	:: "" ;
"""

from pyparsing import *
from base64 import b64decode
import pprint
import re
import sys

def verifyLen(s,l,t):
    t = t[0]
    if t.len is not None:
        t1len = len(t[1])
        if t1len != t.len:
            raise ParseFatalException(s,l,\
                    "invalid data of length %d, expected %s" % (t1len, t.len))
    return t[1]

# define punctuation literals
LPAR, RPAR, LBRK, RBRK, LBRC, RBRC, VBAR = map(Suppress, "()[]{}|")

decimal = Regex(r'0|[1-9]\d*').setParseAction(lambda t: int(t[0]))
hexadecimal = ("#" + OneOrMore(Word(hexnums)) + "#")\
                .setParseAction(lambda t: int("".join(t[1:-1]),16))
bytes = Word(printables)
raw = Group(decimal("len") + Suppress(":") + bytes).setParseAction(verifyLen)
token = Word(alphanums + "-./_:*+=")
base64_ = Group(Optional(decimal|hexadecimal,default=None)("len") + VBAR 
    + OneOrMore(Word( alphanums +"+/=" )).setParseAction(lambda t: b64decode("".join(t)))
    + VBAR).setParseAction(verifyLen)
    
qString = Group(Optional(decimal,default=None)("len") + 
                        dblQuotedString.setParseAction(removeQuotes)).setParseAction(verifyLen)
smtpin = Regex(r'\&?\d+').setParseAction(lambda t: t[0])
#simpleString = base64_ | raw | decimal | token | hexadecimal | qString | smtpin 

# extended definitions
decimal = Regex(r'-?0|[1-9]\d*').setParseAction(lambda t: int(t[0]))
real = Regex(r"[+-]?\d+\.\d*([eE][+-]?\d+)?").setParseAction(lambda tokens: float(tokens[0]))
token = Word(alphanums + "-./_:*+=!<>")

#simpleString = real | base64_ | raw | smtpin | decimal | token | hexadecimal | qString
simpleString = raw | smtpin | decimal | token | hexadecimal | qString

display = LBRK + simpleString + RBRK
string_ = Optional(display) + simpleString

sexp = Forward()
sexpList = Group(LPAR + ZeroOrMore(sexp) + RPAR)
sexp << ( string_ | sexpList )
    
######### Test data ###########
test1 = """
(edif kovan_dvt1_PrjPcb
  (edifVersion 2 0 0)
  (edifLevel 0)
  (keywordMap
     (keywordLevel 0)
  ))
"""

test2 = """
(
 (Net M_SERVO3
  (Joined    (PortRef &13 (InstanceRef U600))
             (PortRef R7 (InstanceRef U800))
  )
 )
 (Net M_SERVO2
  (Joined    (PortRef &5 (InstanceRef U600))
             (PortRef V9 (InstanceRef U800))
  )
)
)
"""

test3 = """
(                                                 
    (cell Everest_ES8328
      (cellType GENERIC)
      (view netListView
        (viewType NETLIST)
        (interface
          (port (rename &1 "1")   (direction INPUT))
          (port (rename &14 "14") (direction OUTPUT))
          (port (rename &17 "17") (direction INOUT))
        )
      )
    )

 (Net M_SERVO3                                                                                    
  (Joined    (PortRef &13 (InstanceRef U600))                                          
             (PortRef R7 (InstanceRef U800))                                                                           
  )                                                                                                      
 )
                                                                                                               
 (Net (rename M_SERVO2 "M.SERVO2")
  (Joined    (PortRef &5 (InstanceRef U600))  
             (PortRef V9 (InstanceRef U800))                                                            
  )                                                                                                 
)                                                                                                         
)                                       
"""

### code

# just a debug routine to print the nets as read in
def netPrint1(netlist, level):
    for expr in netlist:
        if isinstance(expr, list):
            netPrint1(expr, level+1)
        else:
            print " "*level*2, expr

# this procedure determins if a list has any nested lists inside of it.
# returns true if there are, false if there are no list elements inside the list
def hasLists(input_list):
    for item in input_list:
        if( isinstance(item, list) ):
            return True
    return False

# this procedure recursively descends an interpreted netlist and does 
# rename mappings so as to disambiguate any names for the UCF output
def netRename(netlist, renamed):
    niter = netlist[:]
    for elem in niter:
        if isinstance(elem, list):
            if( hasLists( elem ) ):
                renamed.append(netRename(elem, []))
            else:
                if( elem[0] == 'rename' ):
#                    print elem
                    renamed.append( elem[1] )
                else:
                    renamed.append(elem)
        else:
            # primitives just get returned as base leaves
            renamed.append(elem)

    return renamed

# this procedure extracts a netlist from a parsed EDIF file
# it preserves the structure of the netlist heirarchically
# the result is a nested list, where the top level lists each
# correspond to a net, and behind each net's list is a variable-length
# list of [port, designator] pairs
def netExtract1(netlist, netPinsList):
    nextID = 0
    nextIDcode = ""
    for expr in netlist:
        if isinstance(expr, list):
            netExtract1(expr, netPinsList)
        else:
            if( nextID == 0 ):
                if( expr == "Net" ):
                    nextID = 1
                    nextIDcode = "Net"
                elif( expr == "PortRef" ):
                    nextID = 1
                    nextIDcode = "PortRef"
                elif( expr == "InstanceRef" ):
                    nextID = 1
                    nextIDcode = "InstanceRef"
                elif( expr == "rename" ):
                    nextID = 1
                    nextIDcode = "rename"
                else:
                    nextID = 0
#                    nextIDcode = ""
                continue
            else:
                nextID = 0
                if( nextIDcode == "Net" ):
#                    print expr
                    netPinsList.append([expr])
                elif( nextIDcode == "rename" ):
#                    print expr
                    netPinsList.append([expr])
                elif( nextIDcode == "PortRef" ):
#                    import pdb; pdb.set_trace()
                    if( len(netPinsList[-1:][0]) > 1 ):
                        netPinsList[-1][1].append([re.sub('&','',expr)])
                    else:
                        netPinsList[-1:][0].append([[re.sub('&','',expr)]])
                elif( nextIDcode == "InstanceRef" ):
                    if( len(netPinsList[-1][1]) > 1):
                        netPinsList[-1:][0][-1][-1].append(expr)
                    else:
                        netPinsList[-1:][0][-1][0].append(expr)
#                print " "*level*2, expr


#                    if( isinstance(netPinsList[-1:][0][-1], list) and (netPinsList[-1:][0][-1] != []) ):
#                        netPinsList[-1:][0][1].append([re.sub('&','',expr)])
#                        netPinsList[-1:][0][-1].append(re.sub('&','',expr))
#                    else:
#                        netPinsList[-1:][0].append([[re.sub('&','',expr)]])


# top function for the above recursive call. Sort of inelegant but meh.
def netExtractTop(netlist):
    netPinsList = []
    netExtract1(netlist, netPinsList)
    return netPinsList

# This function takes in the interpreted netlist, finds all elements corresponding
# to the FPGA's designator, and prints UCF-compatible mappings. It also consults a
# regex list of io standard mappings to create IOSTANDARD entries as well.
def netPrintUCF(netlist, designator):
    usedDesignators = []
    for node in netlist:
        listofpins = node[1]
        extraNets = 0
        printLine = ''
        for pins in listofpins:
#            import pdb; pdb.set_trace()
            if( pins[1] == designator ):
                if( usedDesignators.count( node[0] ) == 0 ):
                    printLine = 'NET \"' + node[0] + '\" LOC = ' + pins[0] + ';'
                    # now match against regex list
                    for tup in iostandardMaps:
                        if( re.search( tup[0], node[0] ) ):
                            printStd =  'NET \"' + node[0] + '\" IOSTANDARD = ' + tup[1] + ';'
                            break # important to break once first is found
                    usedDesignators.append( node[0] )
                else:
                    if( extraNets == 0 ):
                        printLine = printLine + '# '
                        extraNets = 1
                    printLine = printLine + pins[0] + " "
        if( printLine != '' ):
            if( extraNets ):
                printLine = "# " + printLine
                printStd = "# " + printStd
            print printLine
            print printStd

### Run tests
t = None
#alltests = [ locals()[t] for t in sorted(locals()) if t.startswith("test") ]
#alltests = [ test1 test2 test3 ]
alltests = []  # no tests

for t in alltests:
    print '-'*50
    print t
    try:
        sexpr = sexp.parseString(t, parseAll=True)
        pprint.pprint(sexpr.asList())
    except ParseFatalException, pfe:
        print "Error:", pfe.msg
        print pfe.markInputline('^')
    print

### actual code
if( len(sys.argv) != 3 ):
    print "Usage: " + sys.argv[0] + " <edif_filename> <fpga_designator>; output to stdout"
    sys.exit(0)
filename = sys.argv[1]
designator = sys.argv[2]

f = open(filename, 'r')
edif = f.read()

#print edif

print "parsing " + filename + "..."
sexpr = sexp.parseString(edif, parseAll=True)
netlist = sexpr.asList()

#netPrint1(netlist, 0)

print "processing rename elements..."
renamed = netRename(netlist, [])
#import pdb; pdb.set_trace()

print "extracting net names..."

pinlist = netExtractTop(renamed)

#pprint.pprint(pinlist)

print "printing netlist..."
pinlist.sort()
netPrintUCF(pinlist, designator)

#### end of code


# other notes:

# we want to assemble data into the following structure:
# net_name : pin_name [pin_name ...]
# based upon the additional criteria of an identifier for the refreence designator

# so as we recurse:
# - we will first hit a "Net" keyword -> next token is net_name
# - we will then search for an InstanceRef keyword -> next token is reference_designator; if match add to net_name
# 
# once we have assembled this list, we will take it and generate UCF-format print output
