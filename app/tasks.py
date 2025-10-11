import queue
import threading
import subprocess
import os
import platform
import re
import shutil
import time

import requests

from app.config import cfg

class Task:
    def __init__(self, loginTuple, name, filepath, folder, gpu, double, force, modern, native, profile):
        self.phase = "Wait"
        self.status = "Waiting"
        self.message = ""
        self.queue = queue.Queue()
        self.threadPipe = None
        self.uploadThread = None

        self.loginTuple = loginTuple
        self.name = name
        self.folder = folder
        self.gpu = gpu
        self.modern = modern
        self.native = native

        self._start_export_phase(name, filepath, folder, double, force, profile)


    def executeMayapy(self, command):
        if platform.system() == "Windows":
            mayapy = f'"C:/Program Files/Autodesk/maya{cfg.mayaVersion.value}/bin/mayapy.exe"'
            command = f"{mayapy} -c \"from maya import standalone; standalone.initialize(); from nemo.pipeline import convert; {command}; standalone.uninitialize()\""
        else:
            mayapy = f"/usr/autodesk/maya{cfg.mayaVersion.value}/bin/mayapy"
            command = [
                mayapy,
                "-c",
                f"from maya import standalone; standalone.initialize(); from nemo.pipeline import convert; {command}; standalone.uninitialize()",
            ]

        env = os.environ.copy()
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        self.threadPipe = threading.Thread(target=Task.enqueue_output, args=(proc.stdout, self.queue))
        self.threadPipe.start()
        return proc

    @staticmethod
    def enqueue_output(proc, queue):
        for line in iter(proc.readline, b""):
            queue.put(line)

    def refresh(self):
        if self.phase == "Failed" or self.phase == "Success":
            return None

        if self.phase == "Upload":
            return None
        else:
            if not self.proc:
                return None

            lines = []
            while True:
                try:
                    line = self.queue.get_nowait()
                    if line:
                        lines.append(line.decode())
                except queue.Empty:
                    break

            result = self.proc.poll()
            newContent = "".join(lines)
            if result is not None:
                output = self.proc.communicate()[0]
                if output:
                    newContent += (
                        f"\n\n================={self.phase} Output=================\n" + output
                    )

                exitCode = self.proc.returncode
                if exitCode == 0:
                    if self.phase == "Export":
                        self.message += newContent
                        self.proc.wait(timeout=1)
                        self.proc = None
                        self._start_upload_phase()
                    elif self.phase == "Assemble":
                        self.phase = "Success"
                        self.status = "Success"
                        self.close()
                else:
                    self.status = f"{self.phase} Error"
                    self.phase = "Failed"
                    self.close()

            self.message += newContent
            return newContent

    def close(self):
        if self.proc:
            self.proc.terminate()
            self.proc = None
        if self.uploadThread and self.uploadThread.is_alive():
            # Note: We can't forcefully terminate a thread in Python
            # The upload thread will finish naturally when the phase changes
            pass

    def active(self):
        return self.proc is not None or (self.uploadThread is not None and self.uploadThread.is_alive())

    def _start_export_phase(self, name, filepath, folder, double, force, profile):
        self.phase = "Export"
        self.status = "Export Running"
        self.message += "\n\n=====================Starting Export Phase=====================\n"

        args = [
            name,
            filepath,
            folder
        ]
        kargs = {
            "double": double,
            "overwrite": force,
            "restoreProfile": profile
        }

        def cast(x):
            return f"'{x}'" if isinstance(x, str) else str(x)

        args = [cast(x) for x in args]
        kargs = [f"{k}={cast(v)}" for k, v in kargs.items()]
        func_call = f"convert.export({','.join(args)}, {','.join(kargs)})"
        self.proc = self.executeMayapy(func_call)

    def _start_upload_phase(self):
        self.phase = "Upload"
        self.status = "Upload Running"
        self.message += "\n\n=====================Starting Upload Phase=====================\n"
        
        self.uploadThread = threading.Thread(target=self._upload_worker)
        self.uploadThread.start()

    def _upload_worker(self):
        url = "https://www.nemopuppet.com/api"

        try:
            message = {
                'username': self.loginTuple[0],
                'password': self.loginTuple[1],
            }

            recv = requests.post(url + '/login', data=message)
            auth = recv.cookies

            files = {'file': open(f'{self.folder}/{self.name}__GRAPH.json', 'rb')}
            message = {'platform': platform.system(), 'gpu': self.gpu}
            recv = requests.post(url + '/tasks', data=message, files=files, cookies=auth)
            farm_task_id = recv.json()['id']
            
            self.message += f"Upload initiated with task ID: {farm_task_id}\n"
            
            elapsed_counter = 0
            while True:
                time.sleep(30)
                
                recv = requests.get(url + f'/task/{farm_task_id}', cookies=auth)
                task_status = recv.json()['status']
                
                if task_status == "Success":
                    self.message += "Server processing completed, downloading result...\n"
                    
                    # Download the result file
                    recv = requests.get(url + f'/artifact/{farm_task_id}', stream=True, cookies=auth)
                    filename = re.findall('filename=\"(.+)\"', recv.headers['content-disposition'])[0]
                    output_path = f'{self.folder}/{filename}'
                    with open(output_path, 'wb') as f:
                        shutil.copyfileobj(recv.raw, f)
                    
                    self.message += f"Downloaded result: {filename}\n"
                    self._start_assemble_phase()
                    break
                elif task_status in ['Error', 'Overtime']:
                    self.status = "Upload Error"
                    self.phase = "Failed"
                    self.message += "Server task failed\n"
                    break
                else:
                    elapsed_counter += 1
                    self.message += f"Task status: {task_status}, {elapsed_counter * 0.5} minutes elapsed. \n"
        except Exception as e:
            self.status = "Upload Error"
            self.phase = "Failed"
            self.message += f"Upload failed: {str(e)}\n"

        
    def _start_assemble_phase(self):
        self.phase = "Assemble"
        self.status = "Assemble Running"
        self.message += "\n\n=====================Starting Assemble Phase=====================\n"
        
        args = [
            f"{self.folder}/{self.name}__EXPORT.zip",
            f"{self.folder}/{self.name}__BINARY.zip",
            f"{self.folder}/maya"
        ]
        kargs = {
            "preview": not self.native,
            "ctrl_proxy": self.modern
        }

        def cast(x):
            return f"'{x}'" if isinstance(x, str) else str(x)

        args = [cast(x) for x in args]
        kargs = [f"{k}={cast(v)}" for k, v in kargs.items()]
        func_call = f"convert.assemble({','.join(args)}, {','.join(kargs)})"
        self.proc = self.executeMayapy(func_call)


tasks = []


def new_task(loginTuple, name, filepath, folder, gpu, double, force, modern, native, profile):
    tasks.append(Task(loginTuple, name, filepath, folder, gpu, double, force, modern, native, profile))


def active_tasks():
    return [task for task in tasks if task.active()]
