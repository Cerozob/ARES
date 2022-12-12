from pathlib import Path
import subprocess
import os
import json
import re
import sys
from loguru import logger

INSTRUAPK_SPLIT = "InstruAPK:"
SEMICOLON_SPLIT = ";;"


class CoverageProcessor(object):
    def __init__(self, device_id: str, apk_package: str, method_locations_path=None):
        self.device_id = device_id
        self.apk_package = apk_package
        self.logcat_position = 0
        self.logcat_current = None
        self.methods_info = {}
        self.uncalled_methods = None
        self.cumulative_uncalled_methods = None
        self.methods_called = {}
        self.cumulative_methods_called = {}
        self.read_number_of_methods_instrumented(method_locations_path)

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

    def get_cumulative_methods_id_called(self):
        return self.cumulative_methods_called

    def get_methods_id_uncalled(self):
        return self.uncalled_methods

    def get_cumulative_methods_id_uncalled(self):
        return self.cumulative_uncalled_methods

    def get_number_of_methods_instrumented(self):
        return self.methods_instrumented

    def get_number_methods_called(self):
        return len(self.methods_called)

    def get_number_cumulative_methods_called(self):
        return len(self.cumulative_methods_called)

    def get_number_methods_uncalled(self):
        return len(self.uncalled_methods)

    def get_number_cumulative_methods_uncalled(self):
        return len(self.cumulative_uncalled_methods)

    def set_methods_instrumented(self, methods_instrumented):
        self.methods_instrumented = methods_instrumented

    def set_logcat_current(self, logcat):
        self.logcat_current = logcat

    def set_logcat_position(self, logcat_line):
        self.logcat_position += logcat_line

    def __read_file_number_of_methods(self, file):
        package_path = r"[\\/]".join(self.get_apk_package().split("."))
        pattern_package = re.compile(r"smali[\\/]" + package_path + r"[\\/](\w+)[\\/]")

        text = file.read().replace("\\", "\\\\")

        data = json.loads(text)
        for key, value in data.items():
            package = re.findall(pattern_package, value["filePath"])
            self.methods_info[key] = {
                "filename": value["fileName"],
                "package": "root" if not package else package[0]
            }

        self.cumulative_uncalled_methods = self.methods_info.copy()

        return len(self.methods_info)

    def read_number_of_methods_instrumented(self, path=None):
        if path is None:
            path = Path.cwd().joinpath(f"{self.get_apk_package()}-locations.json")
        else:
            path = Path(path)
        with open(path) as file:
            self.set_methods_instrumented(self.__read_file_number_of_methods(file))
        file.close()

    def clear_logcat(self):
        command = f"adb -s {self.get_device_id()} logcat -c"
        subprocess.Popen(command)

    def generate_adb_logcat(self):
        command = f"adb -s {self.get_device_id()} logcat -e \"InstruAPK(.)*\" -d"
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.set_logcat_current(process.stdout)
        self.read_logcat()
        return self.get_number_of_methods_instrumented(), self.get_number_methods_called(), self.get_coverage_percentage(), self.get_cumulative_coverage(), self.get_number_cumulative_methods_called(), self.get_number_methods_uncalled(), self.get_number_cumulative_methods_uncalled()

    def read_logcat(self):
        logcat = self.get_logcat_current()
        position = self.get_logcat_position()

        self.read_lines(logcat, position)
        line = logcat.readline().decode('utf-8')
        while line is not None and line != '':
            self.process_line(line)
            self.set_logcat_position(1)
            line = logcat.readline().decode('utf-8')

    def read_lines(self, logcat, lines):
        if lines == 0:
            logcat.readline()
            self.set_logcat_position(1)
        elif lines > 0:
            for i in range(lines):
                logcat.readline()

    def process_line(self, line):
        pattern = re.compile(INSTRUAPK_SPLIT)
        splittedLine = re.split(pattern, line)
        if len(splittedLine) > 1:
            line = splittedLine[1]
            data_method = line.split(SEMICOLON_SPLIT)
            method = data_method[1]
            self.methods_called[method] = self.methods_called.get(method,
                                                                  {"count": 0, "filename": self.methods_info[method][
                                                                      "filename"],
                                                                   "package": self.methods_info[method]["package"]})
            self.methods_called[method]["count"] += 1

            self.cumulative_methods_called[method] = self.methods_called.get(method, {"count": 0,
                                                                                      "filename":
                                                                                          self.methods_info[method][
                                                                                              "filename"],
                                                                                      "package":
                                                                                          self.methods_info[method][
                                                                                              "package"]})
            self.cumulative_methods_called[method]["count"] += 1

            try:
                del self.uncalled_methods[method]
            except KeyError:
                pass

            try:
                del self.cumulative_uncalled_methods[method]
            except KeyError:
                pass
        else:
            logger.info(f"Instruapk line not processed: {line}")

    def get_coverage_percentage(self):
        if self.get_number_of_methods_instrumented() > 0:
            return (self.get_number_methods_called() / self.get_number_of_methods_instrumented()) * 100

    def get_cumulative_coverage(self):
        if self.get_number_of_methods_instrumented() > 0:
            return (self.get_number_cumulative_methods_called() / self.get_number_of_methods_instrumented()) * 100

    def reset(self):
        self.methods_called.clear()
        self.uncalled_methods = self.methods_info.copy()
        self.clear_logcat()

    def clear_cumulative_methods(self):
        self.cumulative_methods_called.clear()
        self.cumulative_uncalled_methods = self.methods_info.copy()


if __name__ == "__main__":
    id_device = sys.argv[1]
    package_name = sys.argv[2]
    coverage_processor = CoverageProcessor(id_device, package_name)  # 'R5CR70M9SMH', 'org.wikipedia'
    # coverage_processor.clear_logcat()
    print(coverage_processor.generate_adb_logcat())
    # coverage_processor = CoverageProcessor('R5CR70M9SMH', 'org.sudowars')
    # coverage_processor.clear_logcat()
    while True:
        print(coverage_processor.generate_adb_logcat())
