import glob
import os
from pathlib import Path
import platform
import subprocess
import argparse
from itertools import zip_longest


def close_old_appium_services():
    system = platform.system()
    if system == 'Windows':
        try:
            subprocess.call(['taskkill', '/F', '/IM', 'node.exe'])
            print('Closed old appium services')
        except Exception as e:
            print(e)
    else:
        os.system('killall node')
        os.system('adb start-server')


def main():
    parser = argparse.ArgumentParser()
    # list of emulators
    parser.add_argument('--list_devices', help='delimited list input', type=str, required=True)
    # put --instr flag in case you want to collect code coverage
    parser.add_argument('--instr_jacoco', default=False, action='store_true')
    parser.add_argument('--instr_emma', default=False, action='store_true')
    parser.add_argument('--instr_instruapk', default=False, action='store_true')
    # parameter to use in case you want to save the policy
    parser.add_argument('--save_policy', default=False, action='store_true')
    parser.add_argument('--reload_policy', default=False, action='store_true')
    # activate this flag in case you want to run ARES on real devices
    parser.add_argument('--real_device', default=False, action='store_true')
    parser.add_argument('--appium_ports', help='delimited list input', type=str, required=True)
    parser.add_argument('--android_ports', help='android ports e.g. 5554 5556 ...', type=str, required=True)
    parser.add_argument('--udids', type=str, required=False)
    # the folders to pick apks from
    parser.add_argument('--path', help='folder of apps', type=str, required=True)
    # set a timer for testing
    parser.add_argument('--timer', help='timer duration', type=int, required=True)
    # select platform version
    parser.add_argument('--platform_version', type=str, default='10.0')
    # how many times do you want to repeat the test ?
    parser.add_argument('--iterations', type=int, default=10)
    # choose one
    parser.add_argument('--algo', choices=['SAC', 'random', 'Q',"DDPG"], type=str, required=True)
    # in case you want to test using timesteps
    parser.add_argument('--timesteps', type=int, required=True)
    # enable if you want to use rotation
    parser.add_argument('--rotation', default=False, action='store_true')
    # enable if you want to toggle internet data
    parser.add_argument('--internet', default=False, action='store_true')
    # in case you are using an emulator you can select between normal or headless (faster)
    parser.add_argument('--emu', choices=['normal', 'headless'], type=str, required=False)
    # Episode duration
    parser.add_argument('--max_timesteps', type=int, default=250)
    # file of strings.txt (one string per line)
    parser.add_argument('--pool_strings', type=str, default='strings.txt')
    parser.add_argument('--trials_per_app', type=str, default=3)
    parser.add_argument('--method_locations_path', type=str, default="org.sudowars-locations.json")
    parser.add_argument('--coverage_report_path', type=str, default="./reports/")

    args = parser.parse_args()
    algo = args.algo
    trials_per_app = args.trials_per_app
    save_policy = args.save_policy
    reload_policy = args.reload_policy
    instr_jacoco = args.instr_jacoco
    instr_emma = args.instr_emma
    instr_instruapk = args.instr_instruapk
    if instr_emma and instr_jacoco:
        raise AssertionError
    rot = args.rotation
    internet = args.internet
    real_device = args.real_device
    emu = args.emu
    close_old_appium_services()
    # Emulator names
    device_names = args.list_devices.split(" ")
    # Appium ports
    appium_ports = [int(p) for p in args.appium_ports.split(" ")]
    android_ports = [int(a_p) for a_p in args.android_ports.split(" ")]
    path = args.path
    apps = glob.glob(f'{path}{os.sep}*.apk')
    app_lists = [list(i) for i in zip_longest(*[apps[i:i + len(android_ports)]
                                                for i in range(0, len(apps), len(android_ports))])]
    for i in range(len(app_lists)):
        app_lists[i] = ','.join(list(filter(None, app_lists[i])))
    timer = args.timer
    timesteps = args.timesteps
    max_timesteps = args.max_timesteps
    pool_strings = args.pool_strings
    android_v = args.platform_version
    iterations = args.iterations
    assert len(device_names) == len(appium_ports) == len(android_ports)
    udids = []
    # Setting emulator names
    if real_device:
        udids = [str(u) for u in args.udids.split(" ")]
    else:
        for port in android_ports:
            udids.append(f'emulator-{port}')

    # print everyting to the console
    # Set app path
    processes = []
    for i in range(len(device_names)):
        
        app = Path(app_lists[i])
        covreport = Path(args.coverage_report_path)
        methodlocs = Path(args.method_locations_path)
        pool = Path(pool_strings)
        
        py = "python"
        script = 'rl_interaction\\test_application.py'
        cmd = [py, script, '--algo', algo, '--appium_port',
               str(appium_ports[i]), '--timesteps', str(timesteps), '--iterations', str(iterations),
               '--udid', str(udids[i]), '--android_port', str(android_ports[i]), '--device_name', device_names[i],
               '--apps', str(app.resolve()), '--max_timesteps', str(max_timesteps), '--pool_strings', str(pool.resolve()),
               '--timer', str(timer), '--platform_version', android_v, '--trials_per_app', str(trials_per_app),
               '--menu']

        
        if emu is not None:
            cmd = cmd + ['--emu', emu]
        if instr_jacoco:
            cmd.append('--instr_jacoco')
        if instr_emma:
            cmd.append('--instr_emma')
        if rot:
            cmd.append('--rotation')
        if internet:
            cmd.append('--internet')
        if save_policy:
            cmd.append('--save_policy')
        if save_policy:
            cmd.append('--reload_policy')
        if real_device:
            cmd.append('--real_device')
        if instr_instruapk:
            cmd.append('--instr_instruapk')
        cmd.append('--method_locations_path')
        cmd.append(str(methodlocs.resolve()))
        cmd.append('--coverage_report_path')
        cmd.append(str(covreport.resolve())+"\\")

        
        if app.is_file():
            print(f'{device_names[i]} is running {app.absolute()}')
        else:
            print(f'path {app.absolute()} not found')
        if pool.is_file():
            print(f'{device_names[i]} is running {pool.absolute()}')
        else:
            print(f'path {pool.absolute()} not found')
        if covreport.is_dir():
            print(f'{device_names[i]} is running {covreport.absolute()}')
        else:
            print(f'path {covreport.absolute()} not found')
        if methodlocs.is_file():
            print(f'{device_names[i]} is running {methodlocs.absolute()}')
        else:
            print(f'path {methodlocs.absolute()} not found')
        
        print(cmd)
        # stdout = subprocess.check_output(cmd, cwd=os.getcwd(), shell=True)
        # print(process.decode('utf-8'))
        processes.append(subprocess.Popen(cmd, cwd=os.getcwd(), shell=True))

    exit_codes = [p.wait() for p in processes]


if __name__ == '__main__':
    main()
