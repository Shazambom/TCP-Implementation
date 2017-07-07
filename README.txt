RELDAT works similarly to the Go Back N procedure described in the book.

The client handles the majority of the logic. Upon starting, the client is given the ip, port, and window size. The client then asks the user to use a transform command or a disconnect command.

In the transform command, the client creates a thread to handle data that is received and a thread to handle sending data. The sending thread sends up to the window size in packets. Every time a packet is
sent, a timeout is started for the packet after which if the packet has not been received, the index the sender uses to send the data is reverted to the index corresponding to the packet after the packet the server has last
received.