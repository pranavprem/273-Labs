"""Code for Lab 1 CMPE 273 Under Suthu Aung Spring 2017 San Jose State University'"""
import psutil
connections = psutil.net_connections("tcp")
final = []
finaldict = {}
#print "----------------"

for connection in connections:
    if connection.pid != None and str(connection.laddr) != "()" and str(connection.raddr) != "()":
        final.append(connection)

for connection in final:
    if connection.pid in finaldict:
        finaldict[connection.pid] = finaldict[connection.pid] + 1
    else:
        finaldict[connection.pid] = 1

sortedDict = sorted(finaldict.items(), key = lambda x: x[1], reverse = True)
#print sortedDict


#print "---------------------"
print '"pid","laddr","raddr","status"'


for sortedDic in sortedDict:
    for connection in final:
        if sortedDic[0] == connection.pid:
            laddrFinal = str(connection.laddr).replace("(", "").replace(")","").replace("'","").split(",")
            raddrFinal = str(connection.raddr).replace("(", "").replace(")","").replace("'","").split(",")
            print '"' + str(connection.pid)+'","'+laddrFinal[0]+"@"+laddrFinal[1].strip()+'","'+raddrFinal[0]+"@"+raddrFinal[1].strip()+'","'+str(connection.status)+'"'
