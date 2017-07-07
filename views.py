"""
Routes and views for the flask application.
"""
import os, time, math
from datetime import datetime
from flask import render_template, request, jsonify, Flask, redirect, url_for
from werkzeug import secure_filename
from wifi import Cell, Scheme
import socket,fcntl,struct
import threading
import serial
import serial.tools.list_ports 
from threading import Timer

app = Flask(__name__)
FilePath = '/home/pi/fusion/File'
LogFilePath = '/home/pi/fusion/log.txt'
UPLOAD_FOLDER = FilePath
ALLOWED_EXTENSIONS = set(['gcode'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
				
Com_Port = '/dev/ttyUSB0'
ser = serial.Serial()
ReceviedData = []
InitDevice = False
MaxRequestTempInfoCount = 5
RequestTempInfoCount = 0
log = open(LogFilePath)

class TimeClock:
    hours = 0
    minutes = 0
    seconds = 0
    def calculate(self):
        if self.seconds == 59:
            self.seconds = 0
            if self.minutes == 59:
                self.minutes = 0
                self.hours = self.hours + 1
            else:
                self.minutes = self.minutes + 1
        else:
            self.seconds = self.seconds + 1
    def Reset(self):
        self.hours = 0
        self.minutes = 0
        self.seconds = 0

MyTimer = TimeClock()
Start_Timing = False

def timer_interval():
    global timer
    if Start_Timing == True:
        timer = Timer(1,timer_interval)
        timer.start()
        MyTimer.calculate()



class PrinterTemp:
    nozzle1 = 0
    nozzle2 = 0
    bed = 0
    def Reset(self):
        self.bed = 0
        self.nozzle1 = 0
        self.nozzle2 = 0

Temperature = PrinterTemp()

class FileToBePrint:
    status = ''
    filename = ''
    file = []
    openfile = []
    totallines = 0
    currentline = 0
    def PrepareData(self):
        self.openfile = open(FilePath +  "/" + self.filename)
        try:
            self.status = 'Ready'
            self.file = self.openfile.readlines()
            self.totallines = len(self.file)
            self.currentline = 0
            return 1
        except:
            self.status = ''
            return 0
        finally:
            self.openfile.close()
    def Reset(self):
        try:
            self.status = ''
            self.filename = ''
            self.file = []
            self.totallines = 0
            self.currentline = 0
            return 1
        except:
            return 0            

def ParseTempInfo(data):
    global Temperature
    global CurrentPrintFile
    if 'ok' in data and 'T'in data and 'B' in data and 'T0' in data:
        Temperature.nozzle1 = data.split(' ')[1].split(':')[1]
        Temperature.bed = data.split(' ')[3].split(':')[1]
    elif 'T' in data and 'E' in data and 'W' in data:
        Temperature.nozzle1 = data.split(' ')[0].split(':')[1]
        CurrentPrintFile.status = 'heating_Nozzle'
    elif 'T' in data and 'E' in data and 'B' in data:
        Temperature.bed = data.split(' ')[2].split(':')[1]
        CurrentPrintFile.status = 'heating_Bed'


def SendGcodeToSerial(line):
    global Next_Printer_Status
    global ser
    global CurrentPrintFile
    global log
    UnRecNum = 0	
    line = line.strip()
    if len(line) > 0:
        if line[0] == '\r' or line[0] == ';' or line[0] == '\n':
            pass
        else:			
            temp = line.split(';')
            ser.write(temp[0] + '\r\n')
            log.write(time.strftime('%Y-%m-%d %X', time.localtime() ) + '  send >> ' + temp[0] + '\r\n')
            Flag = 1
            while Flag and Next_Printer_Status != 'Stop':
		UnRecNum = UnRecNum + 1
                response = ser.readline()
                log.write(time.strftime( '%Y-%m-%d %X', time.localtime() ) + '  recived >> ' + response + '\r\n')
                if 'ok' in response or UnRecNum > 100:
                    Flag = 0
                ParseTempInfo(response)

CurrentPrintFile = FileToBePrint()

Current_Printer_Status = 'Idle'
Next_Printer_Status = 'Idle'
Wifi_Status = 'Unconnected'
USB_to_Serial_Status = 'Unconnected' 

def Idle():
    global CurrentPrintFile
    global Next_Printer_Status
    global Current_Printer_Status
    if Next_Printer_Status == 'Printing':
        result = CurrentPrintFile.PrepareData()
        if result == 1:
            Current_Printer_Status = 'Printing'
        else:
            Next_Printer_Status = 'Stop'
    elif Next_Printer_Status == 'Idle':
        Current_Printer_Status = 'Idle'

def Printing():
    global CurrentPrintFile
    global Next_Printer_Status
    global Current_Printer_Status
    global ser
    if Next_Printer_Status == 'PrintDone':
        Current_Printer_Status = 'PrintDone'
    elif Next_Printer_Status == 'Pause':
        print('pause!')
        Current_Printer_Status = 'Pause'
    elif Next_Printer_Status == 'Stop':
        Current_Printer_Status = 'Stop'
    elif Next_Printer_Status == 'Printing':
        if CurrentPrintFile.currentline < CurrentPrintFile.totallines:
            print(CurrentPrintFile.currentline)
            try:
                ser.flushInput()
                if CurrentPrintFile.currentline > 200:
                    SendGcodeToSerial('M105\r\n')
                SendGcodeToSerial(CurrentPrintFile.file[CurrentPrintFile.currentline])
                CurrentPrintFile.status = 'printing'
            except Exception,e:
                CurrentPrintFile.status = str(e)
                print(e)
                pass
            CurrentPrintFile.currentline = CurrentPrintFile.currentline + 1
        else:
            Next_Printer_Status = 'PrintDone'

def Stop():
    global CurrentPrintFile
    global Next_Printer_Status
    global Current_Printer_Status
    global Star_Printer_Thread
    global ser
    try:
        ser.flushInput()
        ser.flushOutput()
        print('stop!')
        ser.write('G91\r\n')
        ser.write('G1 Z10\r\n')
        ser.write('G28 X0 Y0\r\n')
        CurrentPrintFile.status = 'stop'
        Star_Printer_Thread = False
        Next_Printer_Status = 'Idle'
        Current_Printer_Status = 'Idle'
    except:
        pass

def Pause():
    global CurrentPrintFile
    global Next_Printer_Status
    global Current_Printer_Status
    CurrentPrintFile.status = 'pause'
    if Next_Printer_Status == 'Stop':
        Current_Printer_Status = 'Stop'
    elif Next_Printer_Status == 'Printing':
        Current_Printer_Status = 'Printing'
    elif Next_Printer_Status == 'Pause':
        pass

def PrintDone():
    global Next_Printer_Status
    global Current_Printer_Status
    global Start_Timing
    global CurrentPrintFile
    global Star_Printer_Thread
    global ser
    global log
    try:
        log.close()
        CurrentPrintFile.openfile.close()
        ser.flushInput()
        ser.flushOutput()
        print('done!')
        Start_Timing = False
        CurrentPrintFile.status = 'done'
        Star_Printer_Thread = False
        Current_Printer_Status = 'Idle'
        Next_Printer_Status == 'Idle'
    except:
        pass

def Select_Printer_Status(Current_Printer_Status):
    global Printer_Status
    Printer_Status.get(Current_Printer_Status)()

Printer_Status = {'Idle':Idle,'Printing':Printing,'Stop':Stop,'Pause':Pause,'PrintDone':PrintDone}

Star_Printer_Thread = False
def Printer_Status_Machine():
    global Current_Printer_Status
    global ser
    global Star_Printer_Thread
    while Star_Printer_Thread:
        Select_Printer_Status(Current_Printer_Status)
    print('Thread_Printer_Status_Machine Stop!!!!')
    ser.flushInput()
    ser.flushOutput()

Thread_Printer_Status_Machine = threading.Thread(target=Printer_Status_Machine)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def get_ip_address(ifname): 
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    return socket.inet_ntoa(fcntl.ioctl( 
                s.fileno(), 
                0x8915, # SIOCGIFADDR 
                struct.pack('256s', ifname[:15]) 
                )[20:24])

@app.route('/',methods=['POST', 'GET'])
@app.route('/home',methods=['POST', 'GET'])
def home():
    global FilePath
    global Next_Printer_Status
    global Current_Printer_Status
    global CurrentPrintFile
    global Thread_Printer_Status_Machine
    global Star_Printer_Thread
    global MyTimer
    global Start_Timing
    global Com_Port
    global Temperature
    global ReceviedData
    global ser
    global InitDevice
    global RequestTempInfoCount
    global MaxRequestTempInfoCount
    global timer
    global log
    global LogFilePath
    if request.method == 'POST':
        try:
            print('get a post!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            uploaded_files = request.files.getlist('file')
            print('get files')
            filenames = []
            for file in uploaded_files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        except Exception,e:
            print(e)
        return redirect(url_for('home'))         
    elif request.method == 'GET':
        cmd = request.args.get('cmd')
        if cmd == None:
            try:
                if InitDevice == False:
                    InitDevice = True
                    scheme = Scheme.find('wlan0', 'home')
                    scheme.activate()
            except Exception,e:
                print(e)
                pass
            #try:
            #    ser = serial.Serial(Com_Port, 115200, timeout = 1)
            #    #CurrentPrintFile.Reset()
            #    #MyTimer.Reset()
            #except Exception,e:
            #    print(e)
            #    pass
            pass
        else:
            cmd = cmd.split(':')[0]
            if cmd == "sys_info":
                ssid = 'Unkown'
                usb_to_serial = 'Unkown'
                ip = 'Unkown'
                temperature = '0:0'
                port_list_0 = []
                ReceviedData = []
                response = []
                readTempFlag = 'true'
                try:
                    ip = get_ip_address('wlan0')
                except:
                    pass
                try:
                    scheme = Scheme.find('wlan0', 'home')
                    ssid = scheme.options['wpa-ssid']
                except:
                    pass
                try:
                    port_list = list(serial.tools.list_ports.comports()) 
                    if len(port_list) > 0:
                        port_list_0 =list(port_list[0]) 
                    if ser.isOpen():
                        usb_to_serial = Com_Port
                        #readTempFlag = request.args.get('cmd', 0).split(':')[1]
                        if Current_Printer_Status == 'Idle':
                            if RequestTempInfoCount < MaxRequestTempInfoCount:
                                ser.write('M105\r\n')
                                RequestTempInfoCount = RequestTempInfoCount + 1
                            response = ser.readlines()
                            for res in response:
                                RequestTempInfoCount = 0
                                ReceviedData.append(res)
                                ParseTempInfo(res)
                        temperature = str(Temperature.nozzle1) + ':' + str(Temperature.bed)
                        print(Temperature.nozzle1)             
                    else:
                        ser = serial.Serial(Com_Port, 115200, timeout = 1)
                        usb_to_serial = 'Unkown'
                except:
                    pass
                return jsonify(ip = ip  + "(" + ssid + ")",usb_to_serial = usb_to_serial,print_process_status = CurrentPrintFile.status + ':' + CurrentPrintFile.filename + ':' + str(CurrentPrintFile.totallines) + ':' + str(CurrentPrintFile.currentline), passedTime = str("%02u"%MyTimer.hours) + ':' + str("%02u"%MyTimer.minutes) + ':' + str("%02u"%MyTimer.seconds),temperature = temperature,comlist = port_list_0,receviedData = ReceviedData)
            if cmd == "file":
                filelist = []
                files = os.listdir(FilePath)
                for file in files:
                    filelist.append(file)
                    size = (os.stat(FilePath+'/'+file).st_size)/(1024.0*1024.0)
                    size = round(size,2)
                    filesize = str(size)
                    filelist.append(filesize + "MB")
                return jsonify(filelist = filelist)
            if cmd == "printfile":
                try:
                    if log.closed == False:
                        log.close()
                    log = open(LogFilePath,'w')
                    if ser.isOpen() and Current_Printer_Status =='Idle':
                        CurrentPrintFile.Reset()
                        filename = request.args.get('cmd').split(':')[1].split(';')[0]
                        CurrentPrintFile.filename = filename
                        log.write(filename)
                        Next_Printer_Status = 'Printing'
                        Star_Printer_Thread = True
                        timer = Timer(1,timer_interval)
                        timer.start()
                        MyTimer.Reset()
                        Start_Timing = True
                        Thread_Printer_Status_Machine = threading.Thread(target=Printer_Status_Machine)
                        Thread_Printer_Status_Machine.start()
                except:
                    log.close()
                    pass
                return jsonify(filename = filename)
            if cmd == "pause_print":
                Next_Printer_Status = 'Pause'
                return jsonify()
            if cmd == "start_print":
                Next_Printer_Status = 'Printing'
                return jsonify()
            if cmd == "stop_print":
                log.close()
                try:
                    CurrentPrintFile.openfile.close()
                    ser.flushInput()
                    ser.flushOutput()
                    ser.write('M112\r\n')
                    ser.write('M104 S0\r\n')
                    ser.write('M140 S0\r\n')
                    ser.write("M106 S0\r\n")
                    print('M112\r\n')
                except:
                    pass
                Start_Timing = False
                Next_Printer_Status = 'Stop'
                return jsonify()
            if cmd == "hot_bed":
                if Current_Printer_Status != 'Printing':
                    ser.write('M140 S60\r\n')
                return jsonify()
            if cmd == "cold_bed":
                if Current_Printer_Status != 'Printing':
                    ser.write('M140 S0\r\n')
                return jsonify()
            if cmd == "hot_nozzle_1":
                if Current_Printer_Status != 'Printing':
                    ser.write('M104 S210\r\n')
                return jsonify()
            if cmd == "cold_nozzle_1":
                if Current_Printer_Status != 'Printing':
                    ser.write('M104 S0\r\n')
                return jsonify()
            if cmd == "set_serialport":
                Com_Port = request.args.get('cmd').split(':')[1]
                ser = serial.Serial(Com_Port, 115200, timeout = 1)
                return jsonify()
            if cmd == "poweroff":
                os.system('sudo shutdown -h now')
                return jsonify()
            if cmd == "reboot":
                os.system('sudo reboot')
                return jsonify()
            if cmd == "SerialCMD":
                try:
                    if ser.isOpen() and Current_Printer_Status == 'Idle':
                        serialCMD = request.args.get('cmd').encode("ascii").split(':')[1]
                        if Current_Printer_Status == 'Idle':
                            ser.flushInput()
                            ser.flushOutput()
                            re = ser.write(serialCMD)
                            print(re)
                except Exception,e:
                    print(e)
                return jsonify(result = serialCMD)
            if cmd == "wifi":
                wifilist = []
                try:
                    cell = Cell.all('wlan0')
                    for wifi in cell:
                        s = wifi.ssid + ';' + 'signal : ' + str(wifi.signal) + ';' + 'encryption_type : ' + wifi.encryption_type
                        s = s.replace(' ','&nbsp')
                        wifilist.append(s)
                except:
                    pass
                return jsonify(wifilist = wifilist)
            if cmd == "connect_wifi":
                try:
                    ssid = request.args.get('cmd').split(':')[1].split(';')[0]
                    passwd = request.args.get('cmd').split(':')[1].split(';')[1]
                    print(ssid + ":" + passwd)
                    cell = Cell.all('wlan0')
                    result = ''
                    for wifi in cell:
                        if str(wifi.ssid) == str(ssid):
                            scheme = Scheme.for_cell('wlan0', 'home', wifi, str(passwd))
                            scheme.delete()
                            scheme.save()
                            scheme.activate()
                            result = scheme.activate()
                            print(result)
                            break
                        else:
                            result = 'wifi_setting_error:'+ ssid
                except Exception,e:
                    print(e)
                    return jsonify(result = e)
                return jsonify(result = result)
            if cmd == "deleteFile":
                par = request.args.get('cmd', 0).encode("ascii").split(':')[1].split(';')
                for file in par:
                    try:
                        os.remove(FilePath + '/' + file)
                    except:
                        pass
                return jsonify(status = 'sucess')
        return render_template('index.html', NavHome = 'active', NavFile = 'none', NavWife = 'none',version = 'Version(1.4)')
		
if __name__ == '__main__':
	app.run(host='0.0.0.0', port=80, debug=False)	
