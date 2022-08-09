#!/usr/bin/python3

#==============================================================================
 #       Author:  Andy Garcia
 #     Language:  Python3 (argparse, random, socket, yaml, os, signal,
 #                         sys, atexit, logzero, logger)
 #   To Compile:  n/a
 #
 #-----------------------------------------------------------------------------
 #
 #  Description:  Daemonized non-blocking networked lottery ticket generator 
 #                over TCP/IP handling high concurrency
 #
 #        Input:  Enter start|stop, optional socket address and port to listen
 #
 #       Output:  Displays status of daemon  
 #
 #    Algorithm:  Generates pseudo-random numbers from a diminishing pool,
 #                stores results into nested lists, then forwards results to 
 #                client.
 #
 #   Required Features Not Included:  
 #
 #   Known Bugs:  n/a
 #
 #Classification: A
 #
#==============================================================================

import argparse, random, socket, yaml, os, signal, sys, atexit, logzero 
from logzero import logger

#Displays help menu and switches that are supported with the program
def programSwitches():

    parser = argparse.ArgumentParser(description="Lottery Ticket Generator.")

    #Adds "-l" switch to choose the address to listen for incoming connections
    parser.add_argument("-l", help="Listen on socket address", type=str, 
                        dest="socketAddress", default="127.0.0.1", 
                        required=False)

    #Adds "-p" switch to choose socket port for listening
    parser.add_argument("-p", help="Listen on socket port", type=int, 
                        dest="socketPort", default=1234, required=False)

    parser.add_argument("actionCommand", nargs='?', default="status")

    args = parser.parse_args()

    #Returns arguments passed
    return args


##Select numbers from diminishing pool for each ticket
def generateNumbers(userArgs):

    #Error handling and exits program for invalid number of tickets        
    if userArgs["numTickets"] <= 0:

        logger.info("The number of tickets must be greater than 0.")
        os._exit(0)

    else:

        #Stores rules based on lottery type chosen
        gameRules = lotteryRules(userArgs)

        #Initalizes list to store selected numbers
        numSelected = []

        #Lottery type with highest number, numbers per set, and sets per ticket
        ticketType = {"max": [50, 7, 3],
                    "649": [49, 6, 1],
                    "lot": [45, 6, 2]}

        #Stores value of highest number allowed for lottery type
        try:

            highestNum = int(ticketType[userArgs['lotteryType']][0])

        #Error handling for casting
        except ValueError as e:

            logger.info(f"Can't cast {ticketType[userArgs['lotteryType']][0]}",
                "as integer.")
        
        #Stores value for amount of numbers per set
        try:  

            numberPerSet = int(ticketType[userArgs['lotteryType']][1])

        #Error handling for casting
        except ValueError as e:

            logger.info(f"Can't cast {ticketType[userArgs['lotteryType']][1]}",
                "as integer.")

        #Stores value for number of sets per ticket
        try:  

            setPerTicket = int(ticketType[userArgs['lotteryType']][2])
        
        #Error handling for casting
        except ValueError as e:

            logger.info(f"Can't cast {ticketType[userArgs['lotteryType']][2]}",
                "as integer.")

        #Creates multiple tickets based on argument provided
        for i in range(userArgs["numTickets"]):

            #Initalizes list to store selected numbers for each ticket
            ticketNumbers = [] 

            #Creates pool of numbers to be randomly chosen for each ticket
            numbersPool = [number for number in range(1, highestNum + 1)]

            #Creates numbers for a set in a ticket
            for j in range(setPerTicket):

                #Initalizes list to store selected numbers for each set
                setNumbers = []

                #Picks numbers from diminishing pool using elements in array
                for k in range(numberPerSet):

                    randomNum = random.randint(0, len(numbersPool) - 1) \
                        if numbersPool else None
                    
                    #Picks numbers if pool is not empty
                    if numbersPool is not None:

                        setNumbers.append(numbersPool[randomNum])
                        numbersPool.pop(randomNum)

                    else:
                        logger.info("The pool of numbers is empty.")
                        os._exit(0)

                #Appends sets of numbers to ticket
                ticketNumbers.append(setNumbers)

            #Appends each ticket into a new list
            numSelected.append(ticketNumbers)

        #Returns list containing numbers for each ticket
        return numSelected, gameRules
    

#Displays rules ticket type
def lotteryRules(userArgs):

    olgMaxRules = """\nOLG Lotto MAX selected, here are the rules:
          Each play includes three sets of numbers.
          Each set consists of seven numbers ranging from 1 to 50.\n\n"""
    
    olg649Rules = """\nOLG Lotto 6/49 selected, here are the rules:
          Each play includes one set of six numbers ranging from 1 to 49.\n\n"""

    olgLottarioRules = """\nOLG Lottario selected, here are the rules:
          Each play includes two sets of numbers. 
          Each set consists of six numbers from from 1 to 45.\n\n"""

    if userArgs["lotteryType"] == "max":

        return olgMaxRules

    elif userArgs["lotteryType"] == "649":

        return olg649Rules

    elif userArgs["lotteryType"] == "lot":

        return olgLottarioRules

    else:

        print(f"Error: could not find rules for {userArgs['lotteryType']}.")


#Creates a listener to accept incoming connections
def createSocket(userArgs):

    #Creates socket number based on address and port
    socketNumber = (userArgs["socketAddress"], userArgs["socketPort"])

    #Creates socket object and error handling
    try:

        socketObject = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socketObject.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    except socket.error as e:

        logger.info(f"Failed to create socket, error code: {e}.")
        

    #Binds socket number to socket object to create daemon and error handling
    try:

        socketObject.bind(socketNumber)

    except socket.error as e:

        #Bind socket using IPv6 if it fails to bind socket using IPv4
        try:

            socketObject = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)
            socketObject.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            socketObject.bind(socketNumber)

        except socket.error as e:

            logger.info(f"Failed to build IPv6 socket, error code: {e}.")
            exit()

    #Listens for incoming connections with a queue up to 5 connections
    socketObject.listen(5)
    
    print(f"\nListening for incoming connections on {userArgs['socketAddress']}"
        , f"port {userArgs['socketPort']}...")

    #Listens for incoming connections and executes upon accepted connections
    while True:

        #Parses socket object for client and host address
        clientSocket, userAddress = socketObject.accept()
        logger.info(f"Connection from {userAddress} has been established!")
        
        #Signal to handle children and prevent zombie processes
        signal.signal(signal.SIGCHLD, signalHandler)

        #Create child of parent process
        try:

            processID = os.fork()

        except OSError as e:

            logger.info(f"Error: Could not create child, error code: {e}")
        
        #Execute instructions for child process
        if processID == 0:

            logger.info(f"Starting child with pid {os.getpid()}")

            #Retrieves client args and sends ticket results to client
            handleChild(clientSocket, userAddress)
            socketObject.close()

            logger.info(f"Closing child with pid {os.getpid()}")

            #Closes child process without cleanup
            os._exit(0)

        #Execute instructions for parent process
        else:
            
            #Releases socket and closes connection after child dies
            handleParent(clientSocket)
            

#Handles the clients request and returns results in datastream
def handleChild(clientSocket, userAddress):

    responseMessage = ("Welcome to Lottery Ticket Generator!\n")

    #Sends welcome message to connected clients
    clientSocket.send(bytes(responseMessage, "utf-8"))
    
    #Listens for incoming commands in existing connections
    while True:

        #Receives data, decodes, and strips trailing new lines
        dataReceived = clientSocket.recv(4096)        
        dataDecoded = dataReceived.decode("utf-8")
        dataDecoded = dataDecoded.rstrip("\n")

        #Converts data received into dictionary and handles errors
        try:

            dataDecoded = yaml.load(dataDecoded)

        #Quit program and close all socket connections
        except ValueError as e:

            logger.info(f"Could not cast as dictionary, error code: {e}")
            clientSocket.close()

        #Generates numbers for tickets
        dataResults, gameRules = generateNumbers(dataDecoded)

        #Counter for tickets per play
        ticketNum = 1

        #Sends ticket numbers to client and handles errors
        try:
            
            responseMessage = gameRules
            #clientSocket.send(bytes(str(gameRules), "utf-8"))
            responseMessage += f"Unique ID: {dataDecoded['uniqueID']}\n\n"

            #Loops through each ticket per play 
            for ticket in dataResults:

                responseMessage += "=" * 30
                responseMessage += f"\nTicket: {ticketNum}\n"

                #Loops through each set in a ticket
                for ticketNumbers in ticket:
                    
                    responseMessage += str(ticketNumbers)
                    responseMessage += "\n"

                responseMessage += "\n"
                ticketNum += 1

        #Closes program on error
        except socket.error as e:

            logger.info(f"Failed to send, error code: {e}.")
            clientSocket.close()
            quit()
        
        #Sends response to client
        clientSocket.send(bytes(responseMessage, "utf-8"))

        #Closes connection after sending results to client
        clientSocket.close()
        logger.info(f"Connection from {userAddress} has been closed!")
        break
        

#Parent process closes client sockets after child process is executed
def handleParent(clientSocket):

    #Releases socket for child process
    clientSocket.close()


#Handles child processes and prevents zombie children        
def signalHandler(signalNumber, signalFrame): 

    #Waits for children process and does not block 
    while True:

        try:
            
            processID, exitStatus = os.waitpid(-1, os.WNOHANG)
        
        except OSError:

            return

        if processID == 0:

            return


#Handles signals for terminating processes
def sigtermHandler(SignalNumber, signalFrame):

    raise SystemExit(1)


#Handles start and stop signals for daemonizing application
def daemonizeApp(userArgs, *, stdin='/dev/null', stdout='/dev/null', 
                 stderr='/dev/null'):

    #Path of PID file
    daemonFile = "/var/run/daemon/DPI912_algarcia1.pid"

    #Starts daemon process if daemon PID file doesn't exist
    if userArgs["actionCommand"] == "start":

        if os.path.exists(daemonFile):

            print("Daemon is already running.")
            raise SystemExit(0)

        #First fork to detach from parent. 
        try:
            
            #Closes parent for detaching child
            if os.fork() > 0:

                raise SystemExit(0)

        except OSError as e:

            raise RuntimeError("Failed to create fork #1.\n")

        #Changes directory and changes permissions to program and file system
        os.chdir('/')
        os.umask(0)
        os.setsid()
     
        #Creates second fork to detach from session leader and terminal
        try:

            #Closes parent for detaching child
            if os.fork() > 0:

                raise SystemExit(0)

        except OSError as e:

            raise RuntimeError("Failed to create fork #2.\n")

        #Flush I/O buffers
        sys.stdout.flush()
        sys.stderr.flush()

        #Replace file descriptors for stdin, stdout, and stderr
        with open(stdin, 'rb', 0) as fileOutput:

            os.dup2(fileOutput.fileno(), sys.stdin.fileno())

        with open(stdout, 'ab', 0) as fileOutput:

            os.dup2(fileOutput.fileno(), sys.stdout.fileno())

        with open(stderr, 'ab', 0) as fileOutput:

            os.dup2(fileOutput.fileno(), sys.stderr.fileno())

        #Checks if directory to hold daemon PID file exists
        if not os.path.exists('/var/run/daemon'):

            #Create directory for daemon PID file and change permissions
            try:

                os.setuid(0)
                os.setgid(0)
                os.mkdir('/var/run/daemon')
                os.system('sudo chown daemon:daemon /var/run/daemon')

                #Adds setuid and setgid bit to daemon directory
                os.chmod('/var/run/daemon', 0o6751)   

                #Adds sticky bit to daemon directory
                os.system('sudo chmod +t /var/run/daemon')

                #Relinquishes elevated privileges
                os.setuid(1)
                os.setuid(1)

            except PermissionError:

               logger.info(f"Could not create directory/permissions for pid",
                        f"{os.getpid()}")

        #Write PID to file
        with open(daemonFile, "w") as fileOutput:

            print(os.getpid(), file=fileOutput)

        #Setuid, Setgid, and Sticky bit for daemon PID file
        os.chmod(daemonFile, 0o6751)
        os.system(f'sudo chmod +t {daemonFile}')

        logger.info(f"Starting daemon with pid {os.getpid()}")
        connections = userArgs['socketAddress'], userArgs['socketPort']
        logger.info(f"Listening for connections on {connections}")

        #Removes daemon PID file if daemon is stopped
        atexit.register(lambda: os.remove(daemonFile))        

        #Signal handler for termination
        signal.signal(signal.SIGTERM, sigtermHandler)

        #Starts application listening for incoming connections
        createSocket(userArgs)

    #Closes daemon if daemon PID file exists
    elif userArgs["actionCommand"] == "stop":

        if os.path.exists(daemonFile):
    
            #Kills daemon with pid value stored in daemon pid file
            with open(daemonFile) as fileOutput:

                os.kill(int(fileOutput.read()), signal.SIGTERM)

            logger.info(f"Stopping daemon")

        else:

            print("Daemon not running", file=sys.stderr)
            raise SystemExit(1)

    #Checks if daemon PID file exists to determine if daemon is running
    elif userArgs["actionCommand"] == "status":

        if os.path.exists(daemonFile):

            print("Daemon is currently running.", file=sys.stderr)
        
        else:

            print("Daemon is not running.", file=sys.stderr)

    else:

        print(f"Usage: {sys.argv[0]} [start|stop|status]", file=sys.stderr)


#Executes program if current file is the main file
if __name__ == "__main__":

    #File path for daemon log file
    daemonLog = "/var/log/DPI912_algarcia1.log"

    #Creates log file with maximum file size of 1MB and log rotation of 3
    logzero.logfile(daemonLog, maxBytes=1e6, backupCount=3, 
                    disableStderrLogger=True)

    #Setuid, Setgid, and Sticky bit for daemon log file
    os.system(f'sudo chown daemon:daemon {daemonLog}')
    os.chmod(daemonLog, 0o6751) 
    os.system(f'sudo chmod +t {daemonLog}')

    #Parses arguments and converts into dictionary
    userArgs = vars(programSwitches())

    daemonizeApp(userArgs)

