#!/usr/bin/python3
# API version 5.0.220222

# Install paramiko -> $ pip install paramiko -> http://www.paramiko.org/installing.html
import paramiko
import os,sys,time
import socket
from time import sleep
from csv import reader

class SSH_TOOL:
    def __init__(self):
        self.client = None
        self.gpascii_client = None
        self.connected = False
        self.ssh_output = None
        self.ssh_error = None
        self.verbose = False

    # Create the SSH connection with the controller and open gpascii
    def connect(self, ip):
        try:
            # Paramiko.SSHClient can be used to make connections to the remote server and transfer files
            print("Establishing ssh connection with {}...".format(ip))
            self.client = paramiko.SSHClient()
            #Parsing an instance of the AutoAddPolicy to set_missing_host_key_policy() changes it to allow any host.
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(hostname = ip, port = 22, username = "root", password = "deltatau", timeout = 5, allow_agent = False, look_for_keys = False)
            print("Connected to the server: ",ip)
            self.connected = True
        except paramiko.AuthenticationException:
            print("Authentication failed, please verify your credentials.")
            return False
        except paramiko.SSHException as sshException:
            print("Could not establish SSH connection: %s" % sshException)
            return False
        except socket.timeout as e:
            print("Connection timeout.")
            return False
        except Exception as e:
            print("Exception during the connecting to the server.")
            print("Python says: ",e)
            self.client.close()
            return False

        self.gpascii_client = self.client.invoke_shell(term = "vt100")
        
        # Flush welcome string in the shell buffer before send command (to avoid read them after and provoke an error on command return)
        for count in range(4):
            self.flush()
            sleep(0.15)
        
        self.execute_gpascii("gpascii -2", 0.5)
        self.execute_gpascii("echo7")

    # Send a command through gpascii
    def execute_gpascii(self, command, wait = 0):
        # Just in case flush the SSH channel
        self.flush()
        
        self.gpascii_client.send(command + "\r\n")
        if self.verbose == True:
            print("Command send: {}".format(command))

        if wait > 0:
            sleep(wait)

        # Wait for response from gpascii
        step = 0.1
        time = 0
        done = False

        while done == False:
            ready = self.gpascii_client.recv_ready()
            timeout = time > 2
            if timeout:
                print("Command response timeout!")
                return ""
            elif ready:
                done = True
            sleep(step)
            time += step

        # Get and clean response
        response = self.gpascii_client.recv(2048)
        response = response.decode()
        response = response.replace(command, "")
        response = response.replace("\r","")
        #response = response.replace("\n"," ")
        response = response.replace("\x06","")
        
        # Remove empty elements
        responseCleaned = ""
        lines = response.split("\n")
        for line in lines:
            if line=="" or line==" ":
                lines.remove(line)
            else:
                responseCleaned += line + "\n"

        #if self.verbose is True:
            #print("Command rcv: {}".format(responseCleaned))   
        return responseCleaned
    
    def flush(self):
        if self.gpascii_client.recv_ready():
            response = self.gpascii_client.recv(2048)

class API:
    def __init__(self):
        # Create ssh channel object
        self.ssh_obj = SSH_TOOL()
        
        self.data = []
        self.column_max = 0
        self.line_max = 0

        self.INIT_ST()

        self.log = False

    def connect(self, ip, verbose = False, log = False):
        self.logfile = open("LOG.txt", "w")
        self.logfile.close()
        self.log = log

        # Connection
        self.ssh_obj.verbose = verbose
        self.ssh_obj.connect(ip)

    def disconnect(self):
        self.ssh_obj.gpascii_client.close()
        self.ssh_obj.client.close()
    
    def executeCommand(self, command):
        answer = self.ssh_obj.execute_gpascii(command)

        #Log command
        if self.log == True:
            self.logfile = open("LOG.txt", "a")
            print("> {}".format(command), file = self.logfile)
            self.logfile.close()
        return answer

    def waitCommandExecuted(self):
      
        elapsedTime = 0
        beginTime = time.process_time()
        delayToWaitSecond = 5

        # For a maximum of 5 seconds
        while elapsedTime < delayToWaitSecond:

                # Wait 100 ms
                time.sleep(0.1)
                elapsedTime += time.process_time() - beginTime
                
                # Ask for command state with c_cmd
                response = self.executeCommand("c_cmd")
                response.replace("\n", "")
                
                if "=" in response:
                    # Get value returned by c_cmd
                    elements = response.split("=", 1)
                    element = elements[1]

                    # Exit if c_cmd return 0 on success or value inferior to 0 on error
                    if int(element) <= 0:						   
                        response = element

                code = int(response)
                
                if code < 0:
                    message = self.CommandReturns[code]
                    print("Command error, code is: {} : {}".format(code, message))                    
                elif self.ssh_obj.verbose == True:
                    print("Command successful: {} Execution time: {} sec".format(response, elapsedTime))	
                return response

        print("Cannot get command return code with c_cmd: timeout! Elapsed time is ", elapsedTime)
        return -1

    def getCommandParameters(self, number = 20):

        # Get the returned parameters by a command
        command = "c_par(0)"
        if number > 1:
            command += ",{},1".format(number)
            
        answer = self.executeCommand(command)
        return answer

    def GetData(self, _column=0, _line=0):
        value = ''                    
        try:
            value = self.data[_line][_column] #get value
            float(value) #test if float (convert string to float)
            return value #return value
        
        except IndexError: #out of tab bounds, raise Exception
            if _column < 0 or _column > self.column_max :
                raise Exception ('Column {} incorrect: column number must be between 1 and {} included.'.format(_column, self.column_max+1))
            elif _line < 0 or _line > self.line_max :
                raise Exception ('Line {} incorrect: line number must be between 1 and {} included.'.format(_line, self.line_max+1))

        except ValueError: #float convertion failed, raise Exception
            raise Exception("Value is not a float.")
    
    def SEQ_DOWNLOAD(self, file_path, pause_stab, pause_mes, dec_nb, cycle_nb):
        try:                        
                #check if parameters are float
                float(pause_stab)
                float(pause_mes)
                int(dec_nb)

                #read file
                self.data = []

                with open(file_path, newline='') as FILE: #open file at specified path
                    #get each line as an array (separates each elements that were separated by space)
                    for row in reader(FILE, delimiter='\t'):
                        #add each line to the data array, creating a 2D array from file content
                        self.data.append(row)
                #get the dimension of our grid
                self.column_max = len(self.data[0])
                self.line_max = len(self.data)
                
                #SEQUENCE
                endline = "\r\n"
                cmd = "open prog 4,256,{}".format(self.line_max) + endline
                cmd += "call motion_sequence_init;" + endline
                cmd += "Q_Gr_Prog_Pause_Duration_s={};".format(pause_stab) + endline
                cmd += "Q_Gr_Prog_Trigger_NbOfTrigger={};".format(pause_mes) + endline
                cmd += "Q_Gr_Prog_Trigger_Period_s={};".format(dec_nb) + endline
                cmd += "Q_Gr_Prog_StartIndex=1;" + endline
                cmd += "Q_Gr_Prog_Cycle_Number={};".format(cycle_nb) + endline
                cmd += "call motion_sequence_start;" + endline

                cmd += "while (Q_Gr_Prog_Seq_Cycle < Q_Gr_Prog_Cycle_Number){" + endline
                cmd += "Q_Gr_Prog_Seq_Cycle++" + endline
                cmd += "if (Q_Gr_Prog_Seq_Cycle == 1){goto (Q_Gr_Prog_StartIndex);}"

                self.executeCommand(cmd)
                
                #set previous line as empty
                lastvalue = ["NONE"]* (self.column_max)

                #for each line
                for line in range(0, self.line_max-1):
                    
                    #start command with line number
                    cmd = "N{}:N{}".format(line+1,line+1)
                       
                    #init an empty new line
                    currentvalue = []

                    #for each column
                    for column in range(0, self.column_max-1):
                        #get current value
                        currentvalue.append(self.GetData(column,line))
                        #add value to command only if different from the value at the previous line
                        if currentvalue[column] != lastvalue[column]:
                            cmd += " Q_Gr_Prog_Seq_aGrX_Cmd({})={}".format(column, currentvalue[column])

                    #save current line as the last used
                    lastvalue = currentvalue
                            
                    #send the whole command for this line
                    cmd += "call motion_move_abs;"
                    self.executeCommand(cmd)

                cmd = "}" + endline
                cmd += "call motion_sequence_end;" + endline
                cmd += "close"
                self.executeCommand(cmd)
                
                print("Sequence downloaded successfully!")

        except ValueError as error: #incorrect paramaters
                print("Error: parameters type not respected: {}".format(error))

        except Exception as exception: #error during reading file
                print("Error: wrong value when reading file: {}".format(exception))
                self.executeCommand("close")

    def SendCommand(self, name, arguments = list(), parametersNumberToRead = 0, waitResponse = True):
        command = ""
        
        if "JOG" in name:
            command += "c_ax={} ".format(arguments[0])
            arguments.pop(0)
            
        # Set cfg flag
        cfg = 1
        # If the command is a get, add c_cfg=0 as prefix else if the command is a set add c_cfg=1
        if "?" in name:
            cfg = 0
            name = name.replace("?","")
        if "CFG_" in name:
            command += "c_cfg={} ".format(cfg)
            
        # Create the parameters part of a command using the given arguments
        for index in range(0, len(arguments)):
            command += "c_par({})={} ".format(index, arguments[index])
            
        # Add the command name at the end
        command += "c_cmd=C_{}".format(name)
        
        # Send the complete command
        answer = self.executeCommand(command)
        
        if waitResponse == True:
            if parametersNumberToRead <= 0:
                # Wait for command execution (answer is 0 on success or inferior to 0 on error)
                answer = self.waitCommandExecuted()
            else:
                # Wait for command execution and get the returned parameters
                self.waitCommandExecuted()
                answer = self.getCommandParameters(parametersNumberToRead)
            
        return answer

    def STATE(self):
        answer = self.executeCommand("s_hexa,50,1")
        #get all lines
        lines = answer.split("\n")
        lines.remove("")
        output = ""
        #for each state
        for index in range(0, len(lines)-1):
            #get status name
            text = self.StatusVariables[index]
            value = lines[index]
            substate = ""

            #expend main status
            if index == 0:
                #split as sub-status
                binaryState = "{0:b}".format(int(lines[index]))
                binSize = len(binaryState)-1
                for current in range(0, len(self.s_hexa)-1):
                    name = self.s_hexa[current]
                    state = 0
                    if current <= len(binaryState)-1:
                        state = binaryState[binSize-current]
                    substate += "   {}: {}\n".format(state, name)
            
            elif index == 1:
                value += ":" + self.s_action[index]

            #expend axis status
            elif index >= 14 and index <= 19:
                #split as sub-status
                binaryState = "{0:b}".format(int(lines[index]))
                binSize = len(binaryState)-1
                for current in range(0, len(self.s_ax)-1):
                    name = self.s_ax[current]
                    state = 0
                    if current <= len(binaryState)-1:
                        state = binaryState[binSize-current]
                    substate += "   {}: {}\n".format(state, name)
            
            output += "{}={}\n".format(text,value)

            if substate != "":
                output += substate
            
        #prepend to output
        answer = output
        return answer

    def ERR_LIST(self):
        answer = self.SendCommand('ERR_LIST?', list(), 20)
        #get all lines
        codeList = answer.split("\n")
        codeList.remove("")
        output = ""
        #only consider the actual codes and display the associated messages
        for error in codeList:
            if "nan" not in error:
                code = int(error)
                message = self.ErrorCodes[code]
                output += "error {}: {}\n".format(error,message)
        answer = output
        return answer

    def INIT_ST(self):
        self.StatusVariables = {0:"s_hexa",
            1:"s_action",
            2:"s_uto_tx",
            3:"s_uto_ty",
            4:"s_uto_tz",
            5:"s_uto_rx",
            6:"s_uto_ry",
            7:"s_uto_rz",
            8:"s_mtp_tx",
            9:"s_mtp_ty",
            10:"s_mtp_tz",
            11:"s_mtp_rx",
            12:"s_mtp_ry",
            13:"s_mtp_rz",
            14:"s_ax_1",
            15:"s_ax_2",
            16:"s_ax_3",
            17:"s_ax_4",
            18:"s_ax_5",
            19:"s_ax_6",
            20:"s_pos_ax_1",
            21:"s_pos_ax_2",
            22:"s_pos_ax_3",
            23:"s_pos_ax_4",
            24:"s_pos_ax_5",
            25:"s_pos_ax_6",
            26:"s_dio_1",
            27:"s_dio_2",
            28:"s_dio_3",
            29:"s_dio_4",
            30:"s_dio_5",
            31:"s_dio_6",
            32:"s_dio_7",
            33:"s_dio_8",
            34:"s_ai_1",
            35:"s_ai_2",
            36:"s_ai_3",
            37:"s_ai_4",
            38:"s_ai_5",
            39:"s_ai_6",
            40:"s_ai_7",
            41:"s_ai_8",
            42:"s_cycle",
            43:"s_index",
            44:"s_err_nr",
            45:"s_reserve_01",
            46:"s_reserve_02",
            47:"s_reserve_03",
            48:"s_reserve_04",
            49:"s_reserve_05"}
        
        self.s_hexa = {0:"Error",
            1:"System initialized",
            2:"Control on",
            3:"In position",
            4:"Motion task running",
            5:"Home task running",
            6:"Home complete",
            7:"Home virtual",
            8:"Phase found",
            9:"Brake on",
            10:"Motion restricted",
            11:"Power on encoders",
            12:"Power on limit switches",
            13:"Power on drives",
            14:"Emergency stop"}

        self.s_action = {0:"None",
            1:"Stop",
            2:"ControlOn",
            3:"ControlOff",
            4:"Home",
            5:"HomeVirtual",
            6:"MovePTP",
            7:"MoveSpecificPos",
            8:"MoveSequence",
            9:"MoveJog",
            10:"Handwheel",
            11:"Maintenance"}

        self.s_ax = {0:"Error",
            1:"Control on",
            2:"In position",
            3:"Motion task running",
            4:"Home task running",
            5:"Home complete",
            6:"Phase found",
            7:"Brake on",
            8:"Home hardware input",
            9:"Negative hardware limit switch",
            10:"Positive hardware limit switch",
            11:"Software limit reached",
            12:"Following error",
            13:"Drive fault",
            14:"Encoder error"}

        self.CommandReturns = {0:"Success.",
            -1:"Undefined error.",
            -10:"Wrong value for parameter at index 0.",
            -11:"Wrong value for parameter at index 1.",
            -12:"Wrong value for parameter at index 2.",
            -13:"Wrong value for parameter at index 3.",
            -14:"Wrong value for parameter at index 4.",
            -15:"Wrong value for parameter at index 5.",
            -16:"Wrong value for parameter at index 6.",
            -17:"Wrong value for parameter at index 7.",
            -18:"Wrong value for parameter at index 8.",
            -19:"Wrong value for parameter at index 9.",
            -20:"Wrong value for parameter at index 10.",
            -21:"Wrong value for parameter at index 11.",
            -22:"Wrong value for parameter at index 12.",
            -23:"Wrong value for parameter at index 13.",
            -24:"Wrong value for parameter at index 14.",
            -25:"Wrong value for parameter at index 15.",
            -26:"Wrong value for parameter at index 16.",
            -27:"Wrong value for parameter at index 17.",
            -28:"Wrong value for parameter at index 18.",
            -29:"Wrong value for parameter at index 19.",
            -30:"Unknown command number.",
            -31:"This configuration command is a 'get' only type.",
            -32:"This configuration command is a 'set' only type.",
            -33:"The axis number do not correspond to an axis defined on the controller.",
            -34:"A stop task is running.",
            -35:"All motors need to be control on.",
            -36:"All motors need to be control off.",
            -37:"Emergency stop is pressed.",
            -38:"A motion task is running.",
            -39:"A home task is running.",
            -40:"Requested move is not feasible.",
            -41:"Power supply of limit switches is off.",
            -42:"Power supply of encoders is off.",
            -43:"A fatal error is present. This type of error needs a controller restart to be removed.",
            -44:"An error is present, error reset is required.",
            -45:"Home is not completed.",
            -46:"Software option not available (can be linked to hardware configuration).",
            -47:"Virtual home: file was created on another controller (different MAC address).",
            -48:"Virtual home: some positions read in file are out of software limits.",
            -49:"Virtual home: file data were stored while hexapod was moving.",
            -50:"Virtual home: no data available.",
            -51:"Command has been rejected because another action is running.",
            -52:"Timeout waiting for home complete status.",
            -53:"Timeout waiting for control on status.",
            -54:"Timeout on motion program start.",
            -55:"Timeout on home task start.",
            -56:"Timeout on virtual home write file task.",
            -57:"Timeout on virtual home delete file task.",
            -58:"Timeout on virtual home read file task.",
            -59:"Timeout on disk access verification task.",
            -60:"Configuration file: save process failed.",
            -61:"Configuration file: loaded file is empty.",
            -62:"Configuration file: loaded data are corrupted.",
            -63:"No access to the memory disk.",
            -64:"File does not exist.",
            -65:"Folder access failed.",
            -66:"Creation of folder tree on the memory disk failed.",
            -67:"Generation or write of the checksum failed.",
            -68:"File read: no data or wrong data size.",
            -69:"File read: no checksum.",
            -70:"File read: incorrect checksum.",
            -71:"File write: failed.",
            -72:"File open: failed.",
            -73:"File delete: failed.",
            -74:"Get MAC address failed.",
            -75:"NaN (Not a Number) or infinite value found.",
            -76:"The coordinate system transformations are not initialized.",
            -77:"A kinematic error is present.",
            -78:"The motor phase process failed (phase search or phase set from position offset).",
            -79:"The motor phase is not found.",
            -80:"Timeout waiting for control off status.",
            -81:"The requested kinematic mode (number) is not defined for the machine.",
            -82:"Timeout waiting for phase found status.",
            -1000:"Internal error: 'RET_Dev_CfS_NaNReturned'.",
            -1001:"Internal error: 'RET_Dev_CfS_FctNotAvailableInKernel'.",
            -1002:"Internal error: 'RET_Dev_CfS_UndefinedCfSType'.",
            -1003:"Internal error: 'RET_Dev_CfS_FIO_UndefinedFioType'.",
            -1004:"Internal error: 'RET_Dev_CfS_FIO_HomeFile_UndefinedAction'.",
            -1005:"Internal error: 'RET_Dev_UndefinedEnumValue'.",
            -1006:"Internal error: 'RET_Dev_LdataCmdStatusIsNegative'.",
            -1007:"Internal error: 'RET_Dev_NumMotorsInCoord_Sup_DEF_aGrQ_SIZE'.",
            -1008:"Internal error: 'RET_Dev_NumMotorsInCoord_WrongNumber'.",
            -1009:"Internal error: 'RET_String_StrCat_DestSizeReached'.",
            -1010:"Internal error: 'RET_String_LengthOverStringSize'.",
            -1011:"Internal error: 'RET_String_AllCharShouldIntBetween_0_255'.",
            -1012:"Internal error: 'RET_String_StrCpy_DestSizeReached'.",
            -1013:"Internal error: 'RET_ErrAction_HomeReset'.",
            -1014:"Internal error: 'RET_Home_StopReceivedWhileRunning'.",
            -1015:"Internal error: 'RET_UndefinedKinAssembly'.",
            -1016:"Internal error: 'RET_WrongPmcConfig'."}

        self.ErrorCodes = {1:"An emergency stop has been pressed.",
            2:"A safety input has been triggered. The status of the inputs is given in the DATA field.",
            3:"A temperature sensor has exceeded the limit threshold. Sensor number is given in DATA field.",
            4:"Controller system status error (Sys.Status).",
            5:"Controller ‘abort all’ input has been triggered. (Sys.AbortAll).",
            6:"Controller watchdog error (Sys.WDTFault).",
            7:"Configuration load error.",
            8:"Configuration failed: a wrong hexapod ID has been detected. Detected ID is given in DATA field.",
            9:"Home task has failed.",
            10:"Virtual home write task has failed.",
            11:"The motion program did not start in the defined timeout.",
            12:"The home task did not start in the defined timeout.",
            13:"A kinematic error has occured. Kinematic error number is given in DATA field.",
            14:"Controller coordinate error status (Coord.ErrorStatus). Error number is given in DATA field.",
            15:"An error has been detected on encoder.",
            16:"Brake should have been engaged as the motor control was off.",
            17:"Controller motor status: Auxiliary fault (AuxFault).",
            18:"Controller motor status: Encoder loss (EncLoss).",
            19:"Controller motor status: Amplifier warning (AmpWarn).",
            20:"Controller motor status: Trigger not found (TriggerNotFound).",
            21:"Controller motor status: Integrated current 'I2T' fault (I2tFault).",
            22:"Controller motor status: Software positive limit reach (SoftPlusLimit).",
            23:"Controller motor status: Software negative limit reach (SoftMinusLimit).",
            24:"Controller motor status: Amplifier fault (AmpFault).",
            25:"Controller motor status: Stopped on hardware limit (LimitStop).",
            26:"Controller motor status: Fatal following error (FeFatal).",
            27:"Controller motor status: Warning following error (FeWarn).",
            28:"Controller motor status: Hardware positive limit reach (PlusLimit).",
            29:"Controller motor status: Hardware negative limit reach (MinusLimit).",
            30:"An application error has occurred. Please refer to the hardware user manual to get more details.",
            200:"",
            201:"Internal error: 'Dev_PmcConfigError'.",
            202:"Internal error: 'Dev_CfS_CallCheckFailed'.",
            203:"Internal error: 'Dev_LdataCmdStatusIsNegative'.",
            204:"Internal error: 'Dev_ForbiddenCallToWaitFct'.",
            205:"Internal error: 'Dev_CoordDefinitionFailed'.",
            206:"Internal error: 'Dev_Capp_StartTimeout'.",
            207:"Internal error: 'Dev_InMotionProg'."}        
