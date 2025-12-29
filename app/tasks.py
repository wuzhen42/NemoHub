import queue
import threading
import subprocess
import os
import platform
import re
import shutil
import time

import requests

from app.config import cfg, get_api_domain

class Task:
    def __init__(self, loginTuple, name, filepath, folder, gpu, double, force, modern, native, profile):
        self.phase = "Wait"
        self.status = "Task"
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
            mayapy = f'"C:/Program Files/Autodesk/maya{cfg.mayaVersion.value}/bin/mayapy.exe"' if not cfg.mayapyPath.value else cfg.mayapyPath.value
            command = f"{mayapy} -c \"from maya import standalone; standalone.initialize(); from nemo.pipeline import convert; {command}; standalone.uninitialize()\""
        else:
            mayapy = f"/usr/autodesk/maya{cfg.mayaVersion.value}/bin/mayapy" if not cfg.mayapyPath.value else cfg.mayapyPath.value
            command = [
                mayapy,
                "-c",
                f"from maya import standalone; standalone.initialize(); from nemo.pipeline import convert; {command}; standalone.uninitialize()",
            ]

        env = os.environ.copy()
        if cfg.nemoModulePath.value:
            env["MAYA_MODULE_PATH"] = os.path.dirname(cfg.nemoModulePath.value) + os.pathsep + env.get("MAYA_MODULE_PATH", "")

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
                        "\n\n=================" + self.phase + " Output=================\n" + output
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
                    self.status = "{phase} {error}".format(phase=self.phase, error="Error")
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
            return "'{x}'".format(x=x) if isinstance(x, str) else str(x)

        args = [cast(x) for x in args]
        kargs = ["{k}={v}".format(k=k, v=cast(v)) for k, v in kargs.items()]
        func_call = "convert.export({args}, {kargs})".format(args=','.join(args), kargs=','.join(kargs))
        self.proc = self.executeMayapy(func_call)

    def _start_upload_phase(self):
        self.phase = "Upload"
        self.status = "Upload Running"
        self.message += "\n\n=====================Starting Upload Phase=====================\n"

        self.uploadThread = threading.Thread(target=self._upload_worker)
        self.uploadThread.start()

    def _upload_worker(self):
        url = f"https://www.{get_api_domain()}/api"

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

            self.message += "Upload initiated with task ID: {id}".format(id=farm_task_id) + "\n"

            elapsed_counter = 0
            while True:
                time.sleep(30)

                recv = requests.get(url + '/task/{id}'.format(id=farm_task_id), cookies=auth)
                task_status = recv.json()['status']

                if task_status == "Success":
                    self.message += "Server processing completed, downloading result..." + "\n"

                    # Download the result file
                    recv = requests.get(url + '/artifact/{id}'.format(id=farm_task_id), stream=True, cookies=auth)
                    filename = re.findall('filename=\"(.+)\"', recv.headers['content-disposition'])[0]
                    output_path = '{folder}/{filename}'.format(folder=self.folder, filename=filename)
                    with open(output_path, 'wb') as f:
                        shutil.copyfileobj(recv.raw, f)

                    self.message += "Downloaded result: {filename}".format(filename=filename) + "\n"
                    self._start_assemble_phase()
                    break
                elif task_status in ['Error', 'Overtime']:
                    self.status = "Upload Error"
                    self.phase = "Failed"
                    self.message += "Server task failed" + "\n"
                    break
                else:
                    elapsed_counter += 1
                    self.message += "Task status: {status}, {minutes} minutes elapsed.".format(status=task_status, minutes=elapsed_counter * 0.5) + " \n"
        except Exception as e:
            self.status = "Upload Error"
            self.phase = "Failed"
            self.message += "Upload failed: {error}".format(error=str(e)) + "\n"
        
    def _start_assemble_phase(self):
        self.phase = "Assemble"
        self.status = "Assemble Running"
        self.message += "\n\n=====================Starting Assemble Phase=====================\n"

        args = [
            "{folder}/{name}__EXPORT.zip".format(folder=self.folder, name=self.name),
            "{folder}/{name}__BINARY.zip".format(folder=self.folder, name=self.name),
            "{folder}/maya".format(folder=self.folder)
        ]
        kargs = {
            "preview": not self.native,
            "ctrl_proxy": self.modern
        }

        def cast(x):
            return "'{x}'".format(x=x) if isinstance(x, str) else str(x)

        args = [cast(x) for x in args]
        kargs = ["{k}={v}".format(k=k, v=cast(v)) for k, v in kargs.items()]
        func_call = "convert.assemble({args}, {kargs})".format(args=','.join(args), kargs=','.join(kargs))
        self.proc = self.executeMayapy(func_call)


tasks = []


def new_task(loginTuple, name, filepath, folder, gpu, double, force, modern, native, profile):
    tasks.append(Task(loginTuple, name, filepath, folder, gpu, double, force, modern, native, profile))


def active_tasks():
    return [task for task in tasks if task.active()]
