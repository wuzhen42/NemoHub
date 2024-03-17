import queue
import threading


class Task:
    def __init__(self, name, folder, proc):
        self.name = name
        self.proc = proc
        self.folder = folder
        self.status = "Running"
        self.message = ""

        def enqueue_output(proc, queue):
            for line in iter(proc.readline, b""):
                queue.put(line)

        self.queue = queue.Queue()
        self.taskOut = threading.Thread(
            target=enqueue_output, args=(self.proc.stdout, self.queue)
        )
        self.taskOut.start()

        self.taskErr = threading.Thread(
            target=enqueue_output, args=(self.proc.stderr, self.queue)
        )
        self.taskErr.start()

    def refresh(self):
        if not self.proc:
            return

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
                    "\n\n=====================Output=====================\n" + output
                )

            exitCode = self.proc.returncode
            if exitCode == 0:
                self.status = "Done"
            else:
                self.status = "Error"
            self.close()

        self.message += newContent
        return newContent

    def close(self):
        self.proc.terminate()
        self.proc = None

    def active(self):
        return self.proc is not None


tasks = []


def new_task(name, folder, proc):
    tasks.append(Task(name, folder, proc))


def active_tasks():
    return [task for task in tasks if task.active()]
