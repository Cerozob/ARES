import argparse
import logging
import os
from pathlib import Path
from re import sub
import time
import warnings

# from rl_interaction.algorithms.DDPGExploration import DDPGAlgorithm
from algorithms.DDPGExploration import DDPGAlgorithm
from algorithms.QLearnExploration import QLearnAlgorithm
from algorithms.SACExploration import SACAlgorithm
from algorithms.RandomExploration import RandomAlgorithm
# from rl_interaction.algorithms.TD3Exploration import TD3Algorithm
# from rl_interaction.algorithms.TestApp import TestApp
import pickle
from utils.utils import AppiumLauncher, EmulatorLauncher, Utils
from RL_application_env import RLApplicationEnv
# from rl_interaction.utils.utils import AppiumLauncher, EmulatorLauncher, Utils
# from rl_interaction.RL_application_env import RLApplicationEnv
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from utils import apk_analyzer
from loguru import logger
import subprocess

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # FATAL
logging.getLogger('tensorflow').setLevel(logging.FATAL)


def save_pickles(algo, app_name, cycle, button_list, activities, bugs, bug_set):
    os.makedirs(os.path.join(os.getcwd(), 'pickle_files'), exist_ok=True)
    prefix = f'{algo}_{app_name}'
    with open(os.path.join('pickle_files', f'{prefix}_buttons_{cycle}.pkl'), 'wb') as file:
        pickle.dump(button_list, file)

    with open(os.path.join('pickle_files', f'{prefix}_activities_{cycle}.pkl'), 'wb') as file:
        pickle.dump(activities, file)

    with open(os.path.join('pickle_files', f'{prefix}_bugs_{cycle}.pkl'), 'wb') as file:
        pickle.dump(bugs, file)

    with open(os.path.join('pickle_files', f'{prefix}_bug_names_{cycle}.pkl'), 'wb') as file:
        pickle.dump(bug_set, file)


def main():
    # Launching appium
    parser = argparse.ArgumentParser(description='instr = True to collect code coverage, algo = RL to use RL or random'
                                                 'to choose random approach')
    parser.add_argument('--timesteps', type=int, default=3600)
    parser.add_argument('--iterations', type=int, default=10)
    parser.add_argument('--instr_jacoco', default=False, action='store_true')
    parser.add_argument('--instr_instruapk', default=False, action='store_true')
    parser.add_argument('--instr_emma', default=False, action='store_true')
    parser.add_argument('--save_policy', default=False, action='store_true')
    parser.add_argument('--reload_policy', default=False, action='store_true')
    parser.add_argument('--real_device', default=False, action='store_true')
    parser.add_argument('--rotation', default=False, action='store_true')
    parser.add_argument('--internet', default=False, action='store_true')
    parser.add_argument('--menu', default=False, action='store_true')
    parser.add_argument('--algo', choices=['SAC', 'random', 'Q', 'DDPG'], type=str, required=True)
    parser.add_argument('--emu', choices=['normal', 'headless'], type=str, required=False, default='normal')
    parser.add_argument('--appium_port', type=int, required=True)
    parser.add_argument('--platform_name', choices=['Android', 'iOS'], type=str, default='Android')
    parser.add_argument('--platform_version', type=str, default='9.0')
    parser.add_argument('--udid', type=str, default='emulator-5554')
    parser.add_argument('--device_name', type=str, default='test0')
    parser.add_argument('--android_port', type=str, default='5554')
    parser.add_argument('--apps', type=str, required=True)
    parser.add_argument('--timer', type=int, default=60)
    parser.add_argument('--max_timesteps', type=int, default=250)
    parser.add_argument('--pool_strings', type=str, default='strings.txt')
    parser.add_argument('--trials_per_app', type=int, default=3)
    parser.add_argument('--method_locations_path', type=str, default="org.sudowars-locations.json")
    parser.add_argument('--coverage_report_path', type=str, default="./reports/")

    args = parser.parse_args()

    adb_path: str = Utils.get_adb_executable_path()

    method_locations_path = args.method_locations_path

    coverage_report_path = Path(args.coverage_report_path)

    get_ime_command = f"{adb_path} -s {args.udid} shell settings get secure default_input_method"
    current_IME = subprocess.check_output(get_ime_command, shell=True).decode("utf-8")

    if not coverage_report_path.exists():
        coverage_report_path.mkdir(parents=True, exist_ok=True)
    if coverage_report_path.is_file():
        coverage_report_path = coverage_report_path.parent

    save_policy = args.save_policy
    reload_policy = args.reload_policy
    max_trials = args.trials_per_app
    if max_trials <= 0:
        raise Exception('max_trials must be > 0')
    timesteps = args.timesteps
    max_timesteps = args.max_timesteps
    pool_strings = args.pool_strings
    N = args.iterations
    instr_jacoco = args.instr_jacoco
    instr_emma = args.instr_emma
    instr_instruapk = args.instr_instruapk
    if instr_emma + instr_jacoco + instr_instruapk > 1:
        print('Only one instrumentation tool can be used')
        raise AssertionError
    real_device = args.real_device
    algo = args.algo
    emu = args.emu
    appium_port = args.appium_port
    platform_name = args.platform_name
    platform_version = args.platform_version
    udid = args.udid
    # Check this in case of name error
    device_name = args.device_name.replace('_', ' ')
    rotation = args.rotation
    internet = args.internet
    merdoso_button_menu = args.menu
    android_port = args.android_port
    apps = [p for p in args.apps.split(",")]
    timer = args.timer

    if emu == 'normal':
        is_headless = False
    else:
        is_headless = True

    # Put all APKs in folder apps

    # path = os.path.join(os.getcwd(), app_path)
    my_log = logger.add(os.path.join('logs', 'logger.log'), format="{time} {level} {message}",
                        filter=lambda record: record["level"].name == "INFO" or "ERROR")

    appium = AppiumLauncher(appium_port)
    if real_device:
        emulator = None
    else:
        emulator = EmulatorLauncher(emu, device_name, android_port)

    if len(apps) == 0:
        raise Exception(f'The folder is empty or the path is wrong')
        exit()
    for application in apps:
        app_name = os.path.basename(os.path.splitext(application)[0])
        logger.info(f'now testing: {app_name}\n')
        cycle = 0
        trial = 0
        coverage_dict_template = {}
        try:
            exported_activities, services, receivers, providers, string_activities, my_package = apk_analyzer.analyze(
                application,
                coverage_dict_template)
            ready = True
        except Exception as e:
            logger.error(f'{e} at app: {application}')
            ready = False
        if ready:
            package = None

            while cycle < N:
                logger.info(f'app: {app_name}, test {cycle} of {N} starting')
                # coverage dir
                coverage_dir = ''
                # Creating coverage directory
                if instr_emma or instr_jacoco:
                    coverage_dir = os.path.join(os.getcwd(), 'coverage', app_name, algo, str(cycle))
                    os.makedirs(coverage_dir, exist_ok=True)
                if instr_instruapk:
                    coverage_dir = coverage_report_path
                # logs dir
                log_dir = os.path.join(os.getcwd(), 'logs', app_name, algo, str(cycle))
                os.makedirs(log_dir, exist_ok=True)

                # Creating the policies directory
                policy_dir = os.path.join(os.getcwd(), 'policies')
                os.makedirs(policy_dir, exist_ok=True)

                # instantiating timer in minutes
                coverage_dict = dict(coverage_dict_template)
                widget_list = []
                bug_set = set()
                visited_activities = []
                clicked_buttons = []
                number_bugs = []

                # os.system(f'{adb_path} -s {udid} install -t -r {application}')
                # result = subprocess.run(
                #     [adb_path, "shell", "su", "0", "find", "/data/data/", "-type", "d", "-name", f'"{my_package}*"'],
                #     capture_output=True)
                # package = result.stdout.decode('utf-8').strip('\n').rsplit('/')[-1]

                try:
                    app = RLApplicationEnv(coverage_dict, app_path=application,
                                           list_activities=list(coverage_dict.keys()),
                                           widget_list=widget_list, bug_set=bug_set,
                                           coverage_dir=coverage_dir,
                                           log_dir=log_dir,
                                           visited_activities=visited_activities,
                                           clicked_buttons=clicked_buttons,
                                           number_bugs=number_bugs,
                                           string_activities=string_activities,
                                           appium_port=appium_port,
                                           internet=internet,
                                           instr_emma=instr_emma,
                                           instr_jacoco=instr_jacoco,
                                           instr_instruapk=instr_instruapk,
                                           method_locations=method_locations_path,
                                           timer_start=time.time(),
                                           algo=algo,
                                           coverage_report=coverage_report_path,
                                           merdoso_button_menu=merdoso_button_menu,
                                           rotation=rotation,
                                           platform_name=platform_name,
                                           platform_version=platform_version,
                                           udid=udid,
                                           pool_strings=pool_strings,
                                           device_name=device_name,
                                           max_episode_len=max_timesteps,
                                           is_headless=is_headless, appium=appium, emulator=emulator,
                                           package=my_package, exported_activities=exported_activities,
                                           services=services, receivers=receivers
                                           )
                    if algo == 'TD3':
                        # algorithm = TD3Algorithm()
                        pass
                    elif algo == 'random':
                        algorithm = RandomAlgorithm()
                    elif algo == 'SAC':
                        algorithm = SACAlgorithm()
                    elif algo == 'Q':
                        algorithm = QLearnAlgorithm()
                    elif algo == 'DDPG':
                        algorithm = DDPGAlgorithm()
                        pass
                    elif algo == 'test':
                        # algorithm = TestApp()
                        pass
                    logger.debug("save_policy value: {}".format(save_policy))
                    flag = algorithm.explore(app, emulator, appium, timesteps, timer, save_policy=save_policy,
                                             reload_policy=reload_policy, app_name=app_name, policy_dir=policy_dir,
                                             cycle=cycle)
                    if flag:
                        with open(f'logs{os.sep}success.log', 'a+') as f:
                            f.write(f'{app_name}\n')
                    else:
                        with open(f'logs{os.sep}error.log', 'a+') as f:
                            f.write(f'{app_name}\n')
                except Exception as e:
                    logger.error(e)
                    flag = False
                try:
                    # bye handler, it has been an honour
                    os.kill(app.bug_proc_pid, 9)
                except Exception:
                    pass
                if flag:
                    try:
                        app.reset()
                        app.driver.quit()
                    except InvalidSessionIdException:
                        pass
                    except WebDriverException:
                        pass
                    logger.remove(app.logger_id)
                    logger.remove(app.bug_logger_id)
                    # save_pickles(algo, app_name, cycle, clicked_buttons, visited_activities, number_bugs, bug_set)
                    logger.info(f'app: {app_name}, test {cycle} of {N} ending\n')
                    cycle += 1
                else:
                    trial += 1
                    try:
                        logger.remove(app.logger_id)
                        logger.remove(app.bug_logger_id)
                    except Exception:
                        pass
                    if trial == max_trials:
                        try:
                            app.driver.quit()
                        except Exception:
                            pass
                        logger.error(f'Too Many Times tried, app: {app_name}, iteration: {cycle}')
                        break
            # in order to avoid faulty behavior we uninstall the application
            # if package:
            #     os.system(f'{adb_path} -s {udid} uninstall {package}')
    if emulator is not None:
        emulator.terminate()
    appium.terminate()
    # restore_ime_command = f'{adb_path} -s {udid} shell ime set {current_IME}'
    restore_ime_command = f'{adb_path} -s {udid} shell ime set com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME'
    os.system(restore_ime_command)
    return 0


if __name__ == '__main__':
    main()
