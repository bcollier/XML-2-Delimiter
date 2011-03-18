#XML 2 Delimiter version 0.10
#Description:
#    Takes a Wikipedia data dump stub meta history file (http://en.wikipedia.org/wiki/Wikipedia:Database_download) in xml format and reformats it
#    to a delimited format such as a tab or comma delimited file.

#Problems in Version 0.10
#    1. DOESN'T handle unicode correctly, see below
#    Unexpected error:<type 'exceptions.UnicodeEncodeError'>Line 3762: Error Processing Revision:
#    <revision>
#      <id>871913</id>
#      <timestamp>2003-04-29T00:10:06Z</timestamp>
#      <contributor>
#        <username>Fare</username>
#        <id>10387</id>
#      </contributor>
#      <minor/>
#      <comment>Migration complete</comment>
#      <text id="871913" />
#    </revision>

#    2. Doesn't pull namespace information, which is very important!
#    3. Delimiter in config file doesn't work (overwriting it now)

import re, urllib, time, os, ConfigParser, datetime, sys
from BeautifulSoup import BeautifulSoup
from time import gmtime, strftime
from progress_bar import ProgressBar

#read settings from config file located in the current working directory (home in linux)
config = ConfigParser.ConfigParser()
config.read('/home/bcollier/Code/xml2delimiter/wpdatawork.cfg')
delimiter=config.get('xmlparse','delimiter', 0)
xmlfile=config.get('xmlparse','xmlfile', 1)
revfile = open(config.get('xmlparse','revoutfile', 1),'w')
errorxmlfile = open(config.get('xmlparse','errorxml', 1),'w')
userfile = open(config.get('xmlparse','useroutfile', 1), 'w')
revxml = open(config.get('xmlparse','revxmlfile',1),'w')
extralinesfile = open(config.get('xmlparse','notincludedlinefile',1),'w')
log = open(config.get('Global','logfile',1), 'w')
pagefile = open(config.get('xmlparse','pagefile', 1),'w')
removeIPRevisions = config.getboolean('xmlparse','removeIPRevs')
debug = config.getboolean('Global','debug')
numlinesinfile = config.getint('xmlparse','xmlfilesize')

delimiter = "\t"   #FIXME this is here because when I read from the cnfg file it literally prints \t in the file

#print out current configuration
log.write("CONFIGURATION\nRemove Revisions: " + str(removeIPRevisions) +"\nSTART TIME: " + strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) +"\n")

#write file headers
revfile.write("rev_id" + delimiter + "pageid" + delimiter + "timestamp" + delimiter + "username" + delimiter + "userid" + delimiter + "comment" + delimiter + "text_id\n")
userfile.write("username" + delimiter + "userid\n")

#print  'time ' + str(datetime.datetime.now().second)


def timeline():
    return " time:" + strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + "\n"

#tagattr=1 if there is only one tag and we are pulling the attribute value
def writeTagContents(tagname, tagattr, soup, endofline, outfile):
    tag = soup.find(tagname)

    if tag:
        if len(tagattr) > 0:
            #get the attribute value since this is a single tag
            if not endofline == 1:
                outfile.write(tag[tagattr] + delimiter)
            else:
                outfile.write(tag[tagattr] + "\n")
        else:
            if not endofline == 1:
                outfile.write(tag.contents[0] + delimiter)
            else:
                outfile.write(tag.contents[0] + "\n")
    else:
        outfile.write(delimiter)
        if debug:
            log.write('no tag found:' + tagname + ' writing delimiter in soup: ' + str(soup))

def getTagContents(tagname, tagattr, soupstring):
    soup = BeautifulSoup(soupstring)
    tag = soup.find(tagname)
    if tag:
        if len(tagattr) > 0:
            #get the attribute value since this is a single tag
            return tag[tagattr]
        else:
            return tag.contents[0]

def cleanString(dirtystring):
    cleanstring = dirtystring.replace(delimiter, "")
    return cleanstring

def processRevision(revblock):
    soup = BeautifulSoup(revblock)

    if removeIPRevisions and not soup.find('username'):
        if debug:
            print "Removed revision from IP:" + str(soup.find('ip').contents[0])
    else:
        revxml.write(revblock)

        writeTagContents('id', "", soup, 0, revfile)
        revfile.write(pageid + delimiter)
        writeTagContents('timestamp', "", soup, 0, revfile)

        if soup.find('contributor'):
            contribsoup = soup.find('contributor')
            contributorblock = BeautifulSoup(str(contribsoup))
            #print contributorblock
            if contributorblock.find('username'):
                writeTagContents('username',"",contributorblock, 0, revfile)
                writeTagContents('id',"",contributorblock, 0, revfile)

                writeTagContents('username',"",contributorblock, 0, userfile)
                writeTagContents('id',"",contributorblock, 1, userfile)
            else:
                writeTagContents('ip',"",contributorblock, 0, revfile)
                revfile.write(delimiter)
        else:
            log.write("Missing Contributor Block:" + revblock)

        writeTagContents('comment', "", soup, 0, revfile)
        writeTagContents('text', 'id', soup, 1, revfile)

#initialize variables
revcount = 0
linecount = 0
revblock = ""
isrevisionblock = False
ispageblock = False
isknownline = False
pagetitle = ""
pageid = ""
pagecount = 0

prog = ProgressBar(linecount, numlinesinfile, 100, mode='dynamic', char='#')

for txtline in open(xmlfile):
    try:
        isknownline = False
        prog.increment_amount()
        linecount += 1
        if isrevisionblock:
            revblock = revblock + txtline
            #start: this is what we do when we've finished a revision
            if txtline.find("</revision>") > 0:
                isrevisionblock = False
                isknownline = True
                try:
                    processRevision(cleanString(revblock))
                except:
                    log.write("Unexpected error:" + str(sys.exc_info()[0]) + "Line " + str(linecount) + ": Error Processing Revision:\n" + revblock)
                    errorxmlfile.write(revblock)

                revcount += 1
                if revcount % 500 == 0:
                    print prog, '\r',
                    sys.stdout.flush()
                    log.write("percent complete: " +str(round((float(linecount)/float(numlinesinfile))*100,6)))
                    log.write("%\n line number " + str(linecount))
                    log.write(" revisions processed:" + str(revcount) + " pages processed: " + str(pagecount) + timeline())


        else:
            if txtline.find("<revision>") > 0:
                isrevisionblock = True
                ispageblock = 0
                revblock = txtline
            else:
                if txtline.find("<page>") > 0:
                    ispageblock = True
                    isknownline = True
                    pagecount += 1
                elif txtline.find("</page>") > 0:
                    ispageblock = False
                    isknownline = True

                if ispageblock:
                    if txtline.find('<title>') > 0 and txtline.find('</title>') > 0:
                        pagetitle = getTagContents('title', "", txtline)
                        pagefile.write(pagetitle + delimiter)
                        isknownline = True
                    elif txtline.find('<id>') > 0 and txtline.find('</id>') > 0:
                        pageid = getTagContents('id', "", txtline)
                        pagefile.write(pageid + "\n")
                        isknownline = True
                if not isknownline:
                    try:
                        extralinesfile.write(txtline)
                    except:
                        log.write("Unexpected error:" + str(sys.exc_info()[0]) + "Line " + str(linecount) + ": Error Processing Line:\n" + txtline)

    except:
        log.write("Wicked Bad error, couldn't process this line even with error catching':" + str(sys.exc_info()[0]) + "Line " + str(linecount))

log.write("PROGAM COMPLETE - FINAL STATISTICS:\n")
log.write("%\n line number " + str(linecount))
log.write(" revisions processed:" + str(revcount) + " pages processed: " + str(pagecount) + timeline())
print "Program Completed at: " + timeline()

revfile.close()
userfile.close()
log.close()
revxml.close()
extralinesfile.close()
pagefile.close()
errorxmlfile.close()
