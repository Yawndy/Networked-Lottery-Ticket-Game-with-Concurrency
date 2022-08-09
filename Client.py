#!/usr/bin/python3

#==============================================================================
 #       Author:  Andy Garcia
 #     Language:  Python3 (random, argparse, socket, os, signal)
 #   To Compile:  n/a
 #
 #-----------------------------------------------------------------------------
 #
 #  Description:  Multi-processing client for networked lottery ticket generator
 #
 #        Input:  Command line switches and arguments.
 #
 #       Output:  Outputs path for file containing datastream results
 #
 #    Algorithm:  Connects to server using child processes to retrieve ticket 
 #                numbers based on the lottery game chosen.
 #
 #   Required Features Not Included:  n/a
 #
 #   Known Bugs:  n/a
 #
 #Classification: B
 #
#==============================================================================

import random, argparse, socket, os, signal

#Displays help menu and switches that are supported with the program
def programSwitches():

    parser = argparse.ArgumentParser(description="Lottery Ticket Generator.")

    #Adds switch to choose between three different lottery types
    parser.add_argument("-t", help="Choose lottery type", type=str, 
                        dest="lotteryType", choices=["649", "max", "lot"], 
                        default="649", required=False)

    #Adds switch to enable multiple tickets
    parser.add_argument("-n", help="Choose number of tickets", type=int, 
                        dest="numTickets", default=1, required=False)

    #Adds switch for choosing socket address
    parser.add_argument("-r", help="Remote socket address", type=str, 
                        dest="socketAddress", default="127.0.0.1", 
                        required=False)
                        
    #Adds switch for choosing socket port 
    parser.add_argument("-p", help="Rmote socket port", type=int,
                        dest="socketPort", default=1234, required=False)

    #Adds switch for requesting unique identifier 
    parser.add_argument("-u", help="Unique Identifier", type=str, 
                        dest="uniqueID", default="0000", required=False)

    parser.add_argument("-c", help="Number of connections", type=int,
                        dest="numConnections", default=1, required=False)

    #Parses arguments
    args = parser.parse_args()
    
    #Returns arguments passed
    return args


#Creates a socket to connect to remote addresses
def socketConnection(userArgs):

    #Filepath to store file with results of each ticket
    outputFilepath = r"/home/lab/results.txt"

    #Creates socket number from parsed arguments
    socketNumber = (userArgs["socketAddress"], userArgs["socketPort"])

    signal.signal(signal.SIGCHLD, signalHandler)     

    #Loops based on the number of connections requested
    for userCounter in range(userArgs["numConnections"]):
        
        processID = os.fork()

        #Child process will execute
        if processID == 0:
            
            #Creates child process to request for ticket
            handleChild(outputFilepath, userCounter, socketNumber)
            exit()
            
    print(f"Note: Data will be written to \"/home/lab/results.txt\"")

#Simulates multiple requests by creating child processes to request tickets
def handleChild(outputFilepath, userCounter, socketNumber):
    
    #List of lottery games for random choice
    lotteryChoices = ["649", "max", "lot"]

    #Creates socket and handles errors on failure
    try:

        socketObject = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socketObject.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    except socket.error as e:

        print(f"Failed to create socket, error code: {e}.")
        exit()

    #Connects to socket and handles errors on failure
    try:

        socketObject.connect(socketNumber)
    
    except socket.error as e:
        
        #Connect to socket using IPv6 if it fails to connect using IPv4
        try:
            
            socketObject = socket.socket(
                                        socket.AF_INET6, 
                                        socket.SOCK_STREAM,
                                        0)
            socketObject.setsockopt(
                                    socket.SOL_SOCKET, 
                                    socket.SO_REUSEPORT,
                                    1)
            socketObject.connect(socketNumber)

        except socket.error as e:

            print(f"Failed to connect to socket, error code: {e}")
            exit()

    #Receives server welcome message
    dataReceived = socketObject.recv(1024)
    dataDecoded = dataReceived.decode("utf-8")

    #Arbitrary arguments for each child of the parent process
    userArgs["uniqueID"] = str(os.getpid()) + str(userCounter)
    userArgs["numTickets"] = random.randint(1,5)
    userArgs["lotteryType"] = random.choice(lotteryChoices)

    #Keep connection alive until message is received.
    while True:

        #Sends arguments to server for ticket results
        try:

            socketObject.send(bytes(str(userArgs), "utf-8"))
        
        except socket.error as e:

            print(f"Failed to send, error code: {e}.")
            exit()

        #Receives message from server then closes connection
        dataReceived = socketObject.recv(4096, socket.MSG_WAITALL)
        dataDecoded = dataReceived.decode("utf-8")
        
        #Outputs decoded data into file
        try:

            #Opens file with append option
            with open(outputFilepath, 'a') as outputFile:

                #Writes data stream to file
                outputFile.write(dataDecoded)

                #Closes socket connection and closes program
                socketObject.close()
                break
            
        #Error handling if not successful
        except Exception as e:

            print(f"Could not write to file in {outputFilepath}")
            socketObject.close()
            break


#Handles fork'd children and prevents zombie children        
def signalHandler(sigNum, sigFrame):

    #Waits for children process and does not block     
    while True:

        try:
            
            processID, exitStatus = os.waitpid(-1, os.WNOHANG)
        
        except OSError:
            
            return
            

        if processID == 0:

            return


if __name__ == "__main__":

    #Stores arguments into a dictionary 
    userArgs = vars(programSwitches())
    
    #Creates socket connection
    socketConnection(userArgs)