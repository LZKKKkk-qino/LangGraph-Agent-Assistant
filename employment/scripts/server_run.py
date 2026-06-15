import os
import subprocess

# text-model THUDM/glm-4-9b-chat
MODEL_PATH = os.environ.get('MODEL_PATH', 'Your_MODEL_PATH')

# vision-model THUDM/glm-4v-9b
# MODEL_PATH = os.environ.get('MODEL_PATH', 'THUDM/glm-4v-9b')


# 开启一个子进程，运行python命令
subprocess.run(["python", "model_server.py", MODEL_PATH])