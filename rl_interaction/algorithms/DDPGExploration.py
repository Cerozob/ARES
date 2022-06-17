import os
import logging
import numpy
from gym import spaces
from stable_baselines3.ddpg.policies import MlpPolicy
from stable_baselines3 import DDPG
from algorithms.ExplorationAlgorithm import ExplorationAlgorithm
from utils.TimerCallback import TimerCallback
from utils.wrapper import TimeFeatureWrapper


logger = logging.getLogger("Traning")


class DDPGAlgorithm(ExplorationAlgorithm):

    @staticmethod
    def explore(app, emulator, appium, timesteps, timer, save_policy=False, app_name='', reload_policy=False,
                policy_dir='.', cycle=0, train_freq=5, target_update_interval=10, **kwargs):
        try:
            env = TimeFeatureWrapper(app)
            # Loading a previous policy and checking file existence
            if reload_policy and (os.path.isfile(f'{policy_dir}{os.sep}{app_name}.zip')):
                # TODO: fix to match env
                # temp_dim = env.action_space.high[0]
                # env.action_space.high[0] = env.env.ACTION_SPACE
                # logger.info(f'Reloading Policy {app_name}.zip')
                # model = DDPG.load(f'{policy_dir}{os.sep}{app_name}', env)
                # env.action_space.high[0] = temp_dim
                pass
            else:
                logger.info('Starting training from zero')
                model = DDPG(MlpPolicy, env, verbose=1, train_freq=train_freq)
            # model.env.envs[0].check_activity() # why?
            callback = TimerCallback(timer=timer, app=app)
            model.learn(total_timesteps=timesteps, callback=callback)
            # It will overwrite the previous policy

            if save_policy:
                # logger.info('Saving Policy...')
                # model.action_space.high[0] = model.env.envs[0].ACTION_SPACE
                # model.save(f'{policy_dir}{os.sep}{app_name}')
                pass

            return True
        except Exception as e:
            print(e)
            # appium.restart_appium()
            # if adapter is not None:
            #     adapter.restart()
            return False
