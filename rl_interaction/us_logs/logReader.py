
from datetime import datetime
from enum import Enum
import subprocess
import sys
import traceback


class FaultType(Enum):
    ERROR = "Error"
    EXCEPTION = "Exception"
    FATAL_EXCEPTION = "FATAL EXCEPTION"


class LogTag(Enum):
    VERBOSE = "V"
    DEBUG = "D"
    INFO = "I"
    WARNING = "W"
    ERROR = "E"
    FATAL = "F"
    SILENT = "S"


class LogLine(object):
    def __init__(self, line: str, index: int):
        self.index = index
        self.rawLine = line
        lineComponents = line.strip().split()
        timestamp = lineComponents[0] if lineComponents[0].isnumeric() else 0
        self.time = datetime.fromtimestamp(float(timestamp))
        self.pid = lineComponents[1]
        self.tid = lineComponents[2]
        self.tag = LogTag(lineComponents[3])
        self.message = " ".join(lineComponents[4:])

    def __str__(self):
        return f"{self.index};{self.time};{self.pid};{self.tid};{self.tag};{self.message}"


class InstrumentationLine(LogLine):
    def __init__(self, line: str, index: int):
        super().__init__(line, index)
        # InstruAPK;;<methodIndex>;;<fileName>;;<methodName>;;<methodParameters>;;<callTimeInMillis>
        lineComponents = self.message.split(";;")
        self.methodIndex = lineComponents[1]
        self.filename = lineComponents[2]
        self.methodName = lineComponents[3]
        self.methodParameters = lineComponents[4:-1]
        timestamp = float(lineComponents[-1])/1000
        self.callTime = datetime.fromtimestamp(timestamp)

    def __str__(self) -> str:
        return f"{self.index};{self.time};{self.pid};{self.tid};{self.tag};{self.message};{self.methodIndex};{self.filename};{self.methodName};{self.methodParameters};{self.callTime}"


class Fault(object):
    def __init__(self, lines: list[LogLine]):
        self.header = lines[0]
        self.lines = lines[1:]
        self.type = FaultType.ERROR if self.header.tag == LogTag.ERROR else FaultType.EXCEPTION
        for fault in FaultType:
            if fault.value in self.header.message:
                self.type = fault
        self.time: datetime = None

    def __str__(self) -> str:
        lines = "\n\t".join([str(line) for line in self.lines])
        return f"{self.header};\n{self.type};{self.time};{lines}"


class LogReader(object):
    def __init__(self, packageName: str, deviceSerial: str = None):
        self.packageName = packageName
        self.device = deviceSerial
        # self.apkFilePath = apkPath
        self.apkPid = None
        self.lastBufferPosition = 0
        self.rawLines, self.instrumentedLines, self.faults = [], [], []
        self.lastCoverageRequest = 0
        self.lastFaultRequest = 0

    def readLog(self):
        newLines, newInstrumentedLines, newFaults = self.readRawLines(self.getLogLines())
        self.rawLines += newLines
        self.instrumentedLines += newInstrumentedLines
        self.faults += newFaults
        return self.rawLines, self.instrumentedLines, self.faults

    def runReadCommand(self, command: list[str]):
        logCollect = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = logCollect.communicate()
        if len(stderr) != 0:
            print(stderr.decode('utf-8'))
        encodedLog = stdout[self.lastBufferPosition:]
        decodedLines = encodedLog.decode('utf-8').splitlines()
        if self.lastBufferPosition >= len(stdout):
            # opcion 1, si las lineas finales son iguales -> no leí nada
            decodedLines = stdout.decode('utf-8').splitlines() if len(stdout) > 0 else [""]
            lastReadLine = self.rawLines[-1].rawLine if len(self.rawLines) > 0 else ""
            if lastReadLine == decodedLines[-1]:
                return []
            # opcion 2, si las lineas finales son diferentes -> leí algo
            else:
                diffIndex = None
                try:
                    diffIndex = decodedLines.index(lastReadLine)+1
                except ValueError:
                    diffIndex = 0
                return decodedLines[diffIndex:]
        else:
            self.lastBufferPosition += len(encodedLog)
        return decodedLines

    def addDeviceSerial(self, command: list[str]):
        if self.device is not None:
            command.append("-s")
            command.append(self.device)
        return command

    def getPIDApk(self, packageName: str) -> str:
        # Get PID of the APK
        command = ['adb']
        command = self.addDeviceSerial(command)
        command.append("shell")
        command.append("pidof")
        command.append("-s")
        command.append(packageName)
        pid = None
        try:
            pid = subprocess.check_output(command).decode('utf-8').strip()
        except subprocess.CalledProcessError as c:
            print(f"app with package name {packageName} was not found")
        if pid is not None and pid.isnumeric():
            pid = int(pid)
        return pid

    def getLogLines(self) -> list[str]:

        logLines = []

        command = ['adb']
        command = self.addDeviceSerial(command)
        command.append('logcat')
        command.append('-v')
        command.append('epoch')
        command.append('-v')
        command.append('threadtime')
        command.append('-d')

        previousPID = self.apkPid
        currentPID = self.getPIDApk(self.packageName)
        if currentPID is None:
            print(f"App with package name {self.packageName} is not currently running")
            if previousPID is None:
                print("No PID found for the app and no previous PID found, no logs to read")
                return []
            else:
                print(f"Previous PID found: {previousPID}")
                print("App is not currently running but was running previously, it may have crashed, logging with previous pid {currentPid}")
        else:
            print(f"App with package name {self.packageName} is currently running with PID {currentPID}")
            if previousPID is None:
                print(f"No previous PID found, logging with PID {currentPID}")
            elif previousPID != currentPID:
                print(f"Previous PID {previousPID} differs from current PID {currentPID}, the app may have restarted or crashed")
                commandPreviousPID = command.copy()
                commandPreviousPID.append(f'--pid={previousPID}')
                logLines += self.runReadCommand(commandPreviousPID)
        command.append(f'--pid={currentPID}')
        logLines += self.runReadCommand(command)
        self.apkPid = currentPID
        return logLines

    def readRawLines(self, lines: list[str]):
        # ["Exception:", "Error:", "FATAL EXCEPTION"]
        faultStartKeywords = [fault.value for fault in FaultType]
        faultReadingKeywords = ["Caused by", ": at ", ": ... ", f"Process: {self.packageName}", "AndroidRuntime: "]
        faultReading = False
        currentFaultLines: list[LogLine] = []
        faults: list[Fault] = []
        # debugInstrumentedLines: list[InstrumentationLine] = []
        instrumentedLines: list[int] = []
        rawLines: list[LogLine] = []
        # line example
        #         1651079062.458 11732 11798 I ProviderInstaller: Installed default security provider GmsCore_OpenSSL
        index = len(self.rawLines)
        for line in lines:
            logLine = None
            if line.startswith("--") or len(line) == 0 or line.isspace():
                continue
            else:
                try:
                    logLine = LogLine(line, index)
                except ValueError as v:
                    print(f"Error parsing line {line}")
                    traceback.print_exc()
                    continue
            rawLines.append(logLine)
            if logLine.message.startswith("InstruAPK"):
                logLine = InstrumentationLine(line, index)
                # debugInstrumentedLines.append(logLine)
                instrumentedLines.append(index)
            if faultReading:
                if any(keyword in logLine.message for keyword in faultReadingKeywords):
                    currentFaultLines.append(logLine)
                else:
                    faultReading = False
                    newFault = Fault(currentFaultLines)
                    faults.append(newFault)
                    currentFaultLines.clear()
            elif logLine.tag == LogTag.ERROR or any(keyword in logLine.message for keyword in faultStartKeywords):
                if not faultReading:
                    faultReading = True
                currentFaultLines.append(logLine)
            index += 1

        return rawLines, instrumentedLines, faults

    def clearLog(self):
        subprocess.check_output(['adb', 'logcat', '-c'])
        self.lastBufferPosition = 0
        return

    def getFaults(self) -> list[Fault]:
        return self.faults

    def getInstrumentedLines(self) -> list[InstrumentationLine]:
        lines: list[InstrumentationLine] = []
        for line in self.instrumentedLines:
            lines.append(self.rawLines[line])
        return lines

    def getNewFaults(self) -> list[Fault]:
        newFaults: list[Fault] = self.faults[self.lastFaultRequest:]
        self.lastFaultRequest = len(self.faults)
        return newFaults

    def getNewInstrumentedLines(self) -> list[InstrumentationLine]:
        newLines: list[InstrumentationLine] = []
        for line in self.instrumentedLines[self.lastInstrumentedRequest:]:
            newLines.append(self.rawLines[line])
        self.lastInstrumentedRequest = len(self.instrumentedLines)
        return newLines


if __name__ == "__main__":
    packageName = sys.argv[1]
    deviceSerial = sys.argv[2] if len(sys.argv) > 2 else None
    logReader = LogReader(packageName, deviceSerial)
    # logReader.clearLog()
    # for testing
    # while True:
    #     rawLines, instrumentedLines, faults = logReader.readLog()
    #     if len(rawLines) > 0:
    #         print(rawLines[0])
    #         print(rawLines[-1])
    #     if len(instrumentedLines) > 0:
    #         print(instrumentedLines[0])
    #         print(instrumentedLines[-1])
    #     if len(faults) > 0:
    #         print(faults[0])
    #         print(faults[-1])
    #     placeholder = 1
