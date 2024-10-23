#!/usr/bin/python3
# API version 5.0.220222

import SYM_HexaPy

ip = "192.168.56.101"

SEQ_file_path = "Gamme_PUNA.txt"
SEQ_pause_stab = 0.1
SEQ_pause_mes = 0.2
SEQ_dec_nb = 1
SEQ_cycle_nb = 2

verbose = False
log = True

# Connect the SSH client
ssh_API = SYM_HexaPy.API()
ssh_API.connect(ip, verbose, log)

if ssh_API.ssh_obj.connected is True:
    
    loop = True
    
    while loop == True:
        # Please refer to the documation for commands arguments
        # Example:
        # Entered: MOVE_PTP 0 1 1 1 2 2 2
        # Command generated and sent: c_par(0)=0 c_par(1)=1 c_par(2)=1 c_par(3)=1 c_par(4)=2 c_par(5)=2 c_par(6)=2 c_cmd=C_MOVE_PTP

        # Get user input
        userInput = input("> ")

        # Check if the input are not null or empty
        invalid = userInput == None or userInput == "" or userInput == " "

        try:
            # Split command on spaces
            arguments = userInput.split()
            # Consider first item as command name
            commandName = arguments[0]
            # Remove the command name to get arguments
            arguments.pop(0)
            
            # Check arguments type (must be floats)
            for arg in arguments:
                float(arg)

            answer = ""

            # Exit loop
            if commandName == 'QUIT':
                loop = False
            #ACTIONS COMMANDS
            elif commandName == 'CLEARERROR':
                answer = ssh_API.SendCommand(commandName)
            elif commandName == 'STOP':
                answer = ssh_API.SendCommand(commandName)
            elif commandName == 'CONTROLON':
                answer = ssh_API.SendCommand(commandName)
            elif commandName == 'CONTROLOFF':
                answer = ssh_API.SendCommand(commandName)
            elif commandName == 'HOME':
                answer = ssh_API.SendCommand(commandName)
            elif commandName == 'HOMEVIRTUAL':
                answer = ssh_API.SendCommand(commandName)
            elif commandName == 'MOVE_PTP':
                answer = ssh_API.SendCommand(commandName, arguments) #arguments: moveType tx ty tz rx ry rz
            elif commandName == 'MOVE_SPECIFICPOS':
                answer = ssh_API.SendCommand(commandName, arguments) #arguments: indexPos
            elif commandName == 'MAINTENANCE':
                answer = ssh_API.SendCommand(commandName, arguments) #arguments: mode axis
            elif commandName == 'MOVE_SEQ':
                answer = ssh_API.SendCommand(commandName)
            elif commandName == 'AXIS_JOG': 
                answer = ssh_API.SendCommand(commandName, arguments) #arguments: axis increment
            elif commandName == 'VALID_PTP':
                answer = ssh_API.SendCommand(commandName, arguments, 1) #arguments: vm moveType tx ty tz rx ry rz
            elif commandName == 'POWER':
                answer = ssh_API.SendCommand(commandName, arguments) #arguments: pwr
            #CONFIGURATION COMMAND
            elif commandName == 'CFG_SAVE':
                answer = ssh_API.SendCommand(commandName, list(), 1)
            elif commandName == 'CFG_SAVE?':
                answer = ssh_API.SendCommand(commandName, list(), 1)
            elif commandName == 'CFG_SAFETYINPUT':
                answer = ssh_API.SendCommand(commandName, arguments, 1) #arguments: bitfield
            elif commandName == 'CFG_SAFETYINPUT?':
                answer = ssh_API.SendCommand(commandName, list(), 1)
            elif commandName == 'CFG_CHANNEL':
                answer = ssh_API.SendCommand(commandName, arguments, 6) #arguments: actuator_1 actuator_2 actuator_3 actuator_4 actuator_5 actuator_6
            elif commandName == 'CFG_CHANNEL?':
                answer = ssh_API.SendCommand(commandName, list(), 12)
            elif commandName == 'CFG_SPEED':
                answer = ssh_API.SendCommand(commandName, arguments, 6) #arguments: translationSpeed angularSpeed
            elif commandName == 'CFG_SPEED?':
                answer = ssh_API.SendCommand(commandName, list(), 6)
            elif commandName == 'CFG_TA':
                answer = ssh_API.SendCommand(commandName, arguments, 3) #arguments: accelerationTime
            elif commandName == 'CFG_TA?':
                answer = ssh_API.SendCommand(commandName, list(), 3)
            elif commandName == 'CFG_CS':
                answer = ssh_API.SendCommand(commandName, arguments, 12) #arguments: txu tyu tzu rxu ryu rzu txo tyo tzo rxo ryo rzo
            elif commandName == 'CFG_CS?':
                answer = ssh_API.SendCommand(commandName, list(), 12)
            elif commandName == 'CFG_LIMIT':
                answer = ssh_API.SendCommand(commandName, arguments, 13) #arguments: lim tx- ty- tz- rx- ry- rz- tx+ ty+ tz+ rx+ ry+ rz+
            elif commandName == 'CFG_LIMIT?':
                answer = ssh_API.SendCommand(commandName, arguments, 13) #arguments: lim
            elif commandName == 'CFG_LIMITENABLE':
                answer = ssh_API.SendCommand(commandName, arguments, 3) #arguments: lim enable
            elif commandName == 'CFG_LIMITENABLE?':
                answer = ssh_API.SendCommand(commandName, list(), 3)
            elif commandName == 'CFG_STALLCURRENT':
                answer = ssh_API.SendCommand(commandName, arguments, 1) #arguments: stallcurrent
            elif commandName == 'CFG_STALLCURRENT?':
                answer = ssh_API.SendCommand(commandName, list(), 1)
            elif commandName == 'CFG_BACKLASH':
                answer = ssh_API.SendCommand(commandName, arguments, 2) #arguments: axis value
            elif commandName == 'CFG_BACKLASH?':
                answer = ssh_API.SendCommand(commandName, list(), 2)
            elif commandName == 'CFG_CONTROL':
                answer = ssh_API.SendCommand(commandName, arguments, 1) #arguments: control
            elif commandName == 'CFG_CONTROL?':
                answer = ssh_API.SendCommand(commandName, list(), 1)
            elif commandName == 'CFG_KIN':
                answer = ssh_API.SendCommand(commandName, arguments, 2) #arguments: kin_mode
            elif commandName == 'CFG_KIN?':
                answer = ssh_API.SendCommand(commandName, list(), 2)
            elif commandName == 'CFG_TUNING':
                answer = ssh_API.SendCommand(commandName, arguments, 1) #arguments: tuning_index
            elif commandName == 'CFG_TUNING?':
                answer = ssh_API.SendCommand(commandName, list(), 1)
            elif commandName == 'CFG_DEFAULT':
                answer = ssh_API.SendCommand(commandName)
            elif commandName == 'CFG_HOME?':
                answer = ssh_API.SendCommand(commandName, list(), 3)
            elif commandName == 'CFG_AXIS_LIMIT?':
                answer = ssh_API.SendCommand(commandName, list(), 12)
            #STATUS COMMAND
            elif commandName == 'VERSION?':
                answer = ssh_API.SendCommand(commandName, list(), 12)
            elif commandName == 'ERR_LIST?':
                answer = ssh_API.ERR_LIST()
            elif commandName == 'ERR_INFO?':
                answer = ssh_API.SendCommand(commandName, arguments, 8) #arguments: index
            elif commandName == 'STATE?':
                answer = ssh_API.STATE()
            #Others
            elif commandName == 'SEQ_DOWNLOAD':
                answer = ssh_API.SEQ_DOWNLOAD(SEQ_file_path, SEQ_pause_stab, SEQ_pause_mes, SEQ_dec_nb,SEQ_cycle_nb)
            elif commandName == 'REBOOT':
                answer = ssh_API.SendCommand("system reboot", list(), 0, False)
            else:
                answer = ssh_API.SendCommand(userInput)

            # Display answer
            print(answer)
            print(answer, file=open("LOG.txt", "a"))
                
        except ValueError:
            print("Command refused: all parameters must be int or float.")

    ssh_API.disconnect()
