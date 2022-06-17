import os
from pathlib import Path
import subprocess

dev1 = ("******","mi9","11.0",4270,5558)
dev2 = ("emulator-5554","avd1","11.0",4273,5554)
dev3 = ("emulator-5556","avd2","11.0",4277,5556)
dev4 =("********","motoe","8.0",4276,5560)

alg1="SAC"
alg2="DDPG"
alg3="Q"
alg4="random"

app = Path(".\\rl_interaction\\apps\\org.sudowars_2-aligned-debugSigned.apk")
covreport = Path(".\\rl_interaction\\reports")
methodlocs = Path(".\\rl_interaction\\org.sudowars-locations.json")
pool = Path(".\\rl_interaction\\strings.txt")

algorithms = [alg1,alg2,alg3,alg4]

devices = [dev4,dev1,dev2]

for dev in devices:
    for alg in algorithms:
        cmdString = f'python rl_interaction\\test_application.py --algo {alg} --appium_port {dev[3]} --iterations 1 --udid {dev[0]} --android_port {dev[4]} --device_name {dev[1]} --apps {str(app.resolve())} --max_timesteps 250 --pool_strings {str(pool.resolve())} --timer 15 --platform_version {dev[2]} --trials_per_app 3 --menu --instr_instruapk --rotation --real_device --method_locations_path {str(methodlocs.resolve())} --coverage_report_path {str(covreport.resolve())}\\'
        print(cmdString)
        process = subprocess.Popen(cmdString.split(), shell=True,cwd=os.getcwd())
        print(f"subprocess started for {alg} on {dev[1]}")
        process.wait()
        print(f"subprocess finished for {alg}")
    print(f"finished for {alg}")
    print("\n")
    