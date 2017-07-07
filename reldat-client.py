#!usr/bin/python
import sys, getopt, socket, pickle, time, os
from thread import *

BUFFER_SIZE = 1000
TIME_OUT = 1
OVERHEAD = 100


index = 0
acked = -1
packetsInTransit = 0
receivingLock = allocate_lock()
packetsLock = allocate_lock()
indexLock = allocate_lock()
ackedLock = allocate_lock()
dataLock = allocate_lock()
receiving = False
packetCount = 0
data = ""

#server stuff
serverIP = ""
port = 0
window = 0


def xorHash(data):
    data = str(data)
    hashLen = 160
    hashVal = 0
    current = 0
    counter = 0
    for char in data:
        counter += 1
        current += (ord(char) << (counter * 2))
        if counter == hashLen:
            counter = 0
            hashVal ^= current
            current = 0
    hashVal = hashVal ^ current

    maxVal = 2 ** hashLen

    hashVal = hex(maxVal - (hashVal % maxVal))

    return hashVal[2:-1]

def assignPacketNumber(arr):
    withPacketNum = []
    for i in range(0, len(arr)):
        withPacketNum.append(pickle.dumps((arr[i], i, xorHash((arr[i], i)))))
    return withPacketNum

def sendData(data, client, ip, port):
    global packetsInTransit
    packetsInTransit += 1
    client.sendto(data, (ip, port))
    print("Sending data: " + str(data))

def timeout(ind):
    time.sleep(TIME_OUT)
    global packetsInTransit
    global acked
    if ind is None or (type(ind) is int and acked < ind):
        packetsLock.acquire()
        packetsInTransit -= 1
        packetsLock.release()
        indexLock.acquire()
        global index
        index = acked + 1
        indexLock.release()

def receiver(client, message):
    global receiving
    global index
    global acked
    global packetsInTransit
    global data
    global packetCount
    receivingLock.acquire()
    receiving = True
    receivingLock.release()
    while acked < len(message) - 1:
        client.settimeout(3)
        try:
            # Tries to receive the information
            recvd = client.recv(BUFFER_SIZE)
            if recvd is not None:
                packetCount += 1
                recvd = pickle.loads(recvd)
                print("Received: " + str(recvd))
                try:
                    ack = int(recvd[1])
                    if ack == acked + 1 and xorHash((recvd[0], recvd[1])) == recvd[2]:
                        dataLock.acquire()
                        data += recvd[0]
                        dataLock.release()
                        ackedLock.acquire()
                        acked += 1
                        ackedLock.release()
                        packetsLock.acquire()
                        packetsInTransit -= 1
                        packetsLock.release()
                except Exception as err:
                    print(err)
                    print("Index was not present in received data.")
                    break
        except Exception as err:
            print(err)
            break
    receivingLock.acquire()
    receiving = False
    receivingLock.release()
    client.close()


def main(argv):
    #Sets up all of the inputs for the file
    args = None
    try:
        opts, args = getopt.getopt(argv, "")
    except getopt.GetoptError:
        print "Please input the ip address, port number, and the window size"
        sys.exit(2)
    global serverIP
    try:
        serverIP = args[0]
    except:
        print "Something went wrong with the IP address"
        sys.exit(2)
    global port
    try:
        port = int(args[1])
    except:
        print "Port was not a number"
        sys.exit(2)
    global window
    try:
        window = int(args[2])
    except:
        print "Window size was not a number"
    #Inputs taken care of

    handshake = pickle.dumps(("syn", -1, xorHash(("syn", -1))))
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.sendto(handshake, (serverIP, port))
    client.settimeout(4)
    try:
        recvd = client.recv(BUFFER_SIZE)
        recvd = pickle.loads(recvd)
        if xorHash((recvd[0], recvd[1])) == recvd[2] and recvd[0] == "SYN" and recvd[1] == -1:
            print("Connection established with server at: " + serverIP)
        else:
            raise Exception("SYN packet did not match.")
    except Exception as err:
        print(err)
        print("Connection establishment failed!")
        sys.exit(0)
    while 1:
        print("Please enter a commmand.")
        arguments = raw_input().split()
        firstWord = ""
        try:
            firstWord = arguments[0]
        except Exception as err:
            print("Please give either 'transform' or 'disconnect' as the first argument.")
        if firstWord.lower() == "transform":
            fileLoc = ""
            try:
                fileLoc = arguments[1]
            except Exception as err:
                print("Please give the file location as the second argument.")
            if fileLoc is not "":
                transform(fileLoc)
        if firstWord.lower() == "disconnect":
            print("Disconnecting")
            sys.exit(2)

def transform(filename):
    message = []
    file = None
    try:
        file = open(filename, "r")
    except:
        print("File not found")
        return
    current = ""
    for line in file:
        for ch in line:
            if sys.getsizeof(current) >= (BUFFER_SIZE - OVERHEAD) - sys.getsizeof(ch):
                message.append(current)
                current = ""
            current += ch
    message.append(current)

    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    global data
    dataLock.acquire()
    data = ""
    dataLock.release()
    message = assignPacketNumber(message)
    print("Sending message to server at: (" + serverIP + ", " + str(port) + ")")

    global index
    global acked
    global packetsInTransit
    global receiving

    # Start receiver thread
    receivingLock.acquire()
    receiving = True
    receivingLock.release()
    start_new_thread(receiver, (client, message))

    while acked < (len(message) - 1) and receiving is True:
        if packetsInTransit < window and index < len(message):
            sendData(message[index], client, serverIP, port)
            #Start timeout thread for every packet, if packet times out, revert index to acked + 1
            start_new_thread(timeout, (index,))
            indexLock.acquire()
            index += 1
            indexLock.release()

    
    if data is not "":
        print "Received data: " + str(data)
        
        output = open(os.path.splitext(filename)[0] + "-received.txt", "w")
        output.write(data)
        output.close()

    print "Number of packets recieved: " + str(packetCount)
    client.close()

if __name__ == "__main__":
    main(sys.argv[1:])