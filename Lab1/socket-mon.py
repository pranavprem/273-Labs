import psutil
connections = psutil.net_connections()
final = []
finaldict = {}
#print "----------------"

for connection in connections:
	if connection.pid != None and connection.laddr!= None and connection.raddr!= None:
		final.append(connection)

for connection in final:
	if connection.pid in finaldict:
		finaldict[connection.pid] = finaldict[connection.pid] + 1
	else:
		finaldict[connection.pid] = 1

sortedDict = sorted (finaldict.items(), key= lambda x: x[1], reverse=True)
print sortedDict



print "---------------------"
print '"pid","laddr","raddr","status"'


for dict in sortedDict:
	for connection in final:
		if dict[0] == connection.pid:
			ladder = str(connection.laddr).split("(")[1].split(")")[0].split(",")
			radder = str(connection.raddr).split("(")[1].split(")")[0].split(",")
			if len(radder)>1 and len(ladder	)>1:
				print '"' + str(connection.pid)+'","'+ladder[0].replace('"',"'")+"@"+ladder[1].strip()+'","'+radder[0].replace('"',"'")+"@"+radder[1].strip()+'","'+str(connection.status)+'"'
