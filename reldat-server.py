#!usr/bin/python
import sys, getopt, socket, pickle, time, Queue
from thread import *

IP = '0.0.0.0'
BUFFER_SIZE = 1000
TIME_OUT = 1
packetsInTransit = 0
packetsLock = allocate_lock()

class SetQueue(Queue.Queue):
    def _init(self, maxsize):
        self.queue = set()
    def _put(self, item):
        self.queue.add(item)
    def _get(self):
        return self.queue.pop()

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

def sendData(data, server, addr):
	global packetsInTransit
	global packetsLock

	packetsLock.acquire()
	packetsInTransit += 1
	packetsLock.release()

	server.sendto(pickle.dumps(data), addr)
	print("Sending data: " + str(data))
	time.sleep(TIME_OUT)

	packetsLock.acquire()
	packetsInTransit -= 1
	packetsLock.release()
	

def main(argv):
	#Sets up all of the inputs for the file

	args = None
	try:
		opts, args = getopt.getopt(argv, "")
	except getopt.GetoptError:
		print "please input a port number and the window size"
		sys.exit(2)
	port = 0
	try:
		port = int(args[0])
	except:
		print "port was not a number"
		sys.exit(2)
	window = 0
	try:
		window = int(args[1])
	except:
		print "window size was not a number"
	#Inputs taken care of

	server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	#Binds the socket to the ip address and port
	server.bind((IP, port))

	packets = SetQueue()
	global packetsInTransit

	print("Binding to ip and port: (" + IP + ", " + str(port)+")")

	while 1:
		#Recieves the data from the socket
		data, addr = server.recvfrom(BUFFER_SIZE)
		try:
			if data is not None:
				data = pickle.loads(data)
				if xorHash((data[0], data[1])) == data[2]:
					print(data[0])
					newPacket = (data[0].upper(), data[1], xorHash((data[0].upper(), data[1])))
					packets.put(newPacket)
			if not packets.empty() and packetsInTransit < window:
				start_new_thread(sendData, (packets.get(), server, addr))
					
		except Exception as err:
			print(str(err))
			server.sendto("error", addr) 



if __name__ == "__main__":
	main(sys.argv[1:])