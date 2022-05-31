usar python 3.8

correr el siguiente comando, cambiando los términos en mayúscula sostenida (Excepto SAC):

python --algo SAC --appium_port 4270 --timesteps 5000 --iterations 2 --udid SERIAL_ANDROID --android_port 5554 --device_name CUALQUIERA --apps RUTA_RELATIVA_ARCHIVO_APK --max_timesteps 250 --pool_strings rl_interaction\\strings.txt --timer 70 --platform_version VERSION_ANDROID --trials_per_app 3 --menu --instr_instruapk --rotation --internet --real_device

probado con:

python --algo SAC --appium_port 4270 --timesteps 5000 --iterations 2 --udid 49296d9c --android_port 5554 --device_name mi9 --apps rl_interaction\\apps\\org.sudowars_2-aligned-debugSigned.apk --max_timesteps 250 --pool_strings rl_interaction\\strings.txt --timer 70 --platform_version 11.0 --trials_per_app 3 --menu --instr_instruapk --rotation --internet --real_device

para ver cambios hechos, en visual studio code usar ctrl+shift+f y buscar "! This is important" o "# !", que fueron overrides de los métodos collect_coverage y bug_handler del archivo RL_application_env.py