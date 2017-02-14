"""Code for Lab 1 CMPE 273 Under Suthu Aung Spring 2017 San Jose State University"""
#Requirement Mapping -- 2. Create a Python script called socket-mon.py.

#Requirement Mapping -- 1. Use psutil and implement a network socket monitoring tool that can check how many TCP sockets are being created by a web application.
import psutil
connections = psutil.net_connections("tcp")

requiredConnections = []
groupingDictionary = {}

#Requirement Mapping -- 3. List all processes that have any socket connections (meaning the laddr and raddr fields exist). 
for connection in connections:
    if connection.pid != None and str(connection.laddr) != "()" and str(connection.raddr) != "()":
        requiredConnections.append(connection)
        if connection.pid in groupingDictionary:
            groupingDictionary[connection.pid] = groupingDictionary[connection.pid] + 1
        else:
            groupingDictionary[connection.pid] = 1

#Requirement Mapping -- 4. Group by the PID and sort the output by the number of the connections per process.
sortedDict = sorted(groupingDictionary.items(), key = lambda x: x[1], reverse = True)

#Requirement Mapping -- 5. Expected Output in CSV format
print '"pid","laddr","raddr","status"'
for sortedDic in sortedDict:
    for connection in requiredConnections:
        if sortedDic[0] == connection.pid:
            laddrFinal = str(connection.laddr).replace("(", "").replace(")","").replace("'","").split(",")
            raddrFinal = str(connection.raddr).replace("(", "").replace(")","").replace("'","").split(",")
            print '"' + str(connection.pid)+'","'+laddrFinal[0]+"@"+laddrFinal[1].strip()+'","'+raddrFinal[0]+"@"+raddrFinal[1].strip()+'","'+str(connection.status)+'"'