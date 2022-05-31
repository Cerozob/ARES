import subprocess
import os
import json
#from Coverage.utils.utils import *
from utils.utils import *
import re
import sys

INSTRUAPK_SPLIT = "InstruAPK:"
SEMICOLON_SPLIT = ";;"

class CoverageProcessor(object):
    def __init__(self, device_id:str, apk_package:str):
        self.device_id = device_id
        self.apk_package = apk_package
        self.logcat_position = 0
        self.logcat_current = None
        self.methods_called = set()
        self.read_number_of_methods_instrumented()

  
    def get_device_id(self):
        return self.device_id

    def get_apk_package(self):
        return self.apk_package
    
    def get_logcat_position(self):
        return self.logcat_position

    def get_logcat_current(self):
        return self.logcat_current

    def get_methods_id_called(self):
        return self.methods_called

    def get_number_of_methods_instrumented(self):
        return self.methods_instrumented

    def get_number_methods_called(self):
        return len(self.methods_called)

    def set_methods_instrumented(self,methods_instrumented):
        self.methods_instrumented = methods_instrumented

    def set_logcat_current(self,logcat):
        self.logcat_current = logcat
    
    def set_logcat_position(self,logcat_line):
        self.logcat_position += logcat_line

    def read_number_of_methods_instrumented(self):
        current_directory = os.getcwd()
        path = os.path.join(current_directory,"Coverage","instrumentation",self.get_apk_package() + '-locations.json' )
        with open(path) as file:        
            self.set_methods_instrumented(read_file_number_of_methods(file))
        file.close()
        
    

    def clear_logcat(self):
        command = f"adb -s {self.get_device_id()} logcat -c"
        subprocess.Popen(command)


    def generate_adb_logcat(self):
        command = f"adb -s {self.get_device_id()} logcat -e \"InstruAPK(.)*\" -d"
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.set_logcat_current(process.stdout)
        self.read_logcat()
        return coverage_processor.get_number_of_methods_instrumented(), coverage_processor.get_number_methods_called(), coverage_processor.get_coverage_percentage()
        
    def read_logcat(self):
        logcat = self.get_logcat_current()
        position = self.get_logcat_position()
        
        self.read_lines(logcat,position)
        line = logcat.readline().decode('utf-8')
        while line is not None and line != '':
            self.process_line(line)
            self.set_logcat_position(1)
            line = logcat.readline().decode('utf-8')
            
    def read_lines(self,logcat,lines):
        if lines == 0:
            logcat.readline()
            self.set_logcat_position(1)  
        elif lines > 0:
            for i in range(lines):
                logcat.readline()
        


       

            
    def process_line(self,line):
        pattern = re.compile(INSTRUAPK_SPLIT)
        line = re.split(pattern,line)[1]
        values = line.split(SEMICOLON_SPLIT)[1]
        self.methods_called.add(values)
        

    def get_coverage_percentage(self):
        if self.get_number_of_methods_instrumented() > 0:
            return (self.get_number_methods_called()/self.get_number_of_methods_instrumented())*100
        
        
# if __name__ == "__main__":
#     id_device = sys.argv[1]
#     package_name = sys.argv[2]
#     coverage_processor = CoverageProcessor(id_device, package_name) #'R5CR70M9SMH', 'org.wikipedia'
#     #coverage_processor.clear_logcat()
#     print(coverage_processor.get_logcat())
coverage_processor = CoverageProcessor('R5CR70M9SMH', 'org.sudowars')
coverage_processor.clear_logcat()
while True: 
    print(coverage_processor.generate_adb_logcat())