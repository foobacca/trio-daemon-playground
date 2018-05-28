#!/usr/bin/env python3
"""
The idea is to have a main loop that waits for user input and:

- start <xyz>
    - start a thread to print <xyz> to the console every 10s for 5 minutes
- status
    - list running jobs
- kill <xyz>
    - kill currently running job with matching name
- stop
    - stops all runnings jobs and exits
"""
import sys

import curio


class StopDaemon(Exception):
    pass


class InvalidCommandError(Exception):
    pass


class Runner:
    sleep_time = 5
    total_run_time = 300
    num_iterations = total_run_time // sleep_time

    def __init__(self, runner_count, xyz):
        self.cancel_event = curio.UniversalEvent()
        self.runner_count = runner_count
        self.xyz = xyz
        self.state = 'init'

    async def run(self):
        """
        print every 10 seconds for 5 minutes
        """
        self.state = 'running'
        try:
            for iter_count in range(self.num_iterations):
                print(
                    "runner number {}, count {}: {}".format(
                        self.runner_count, iter_count, self.xyz
                    )
                )
                try:
                    async with curio.timeout_after(self.sleep_time):
                        await self.cancel_event.wait()
                        print("I've been killed ({}).".format(self.xyz))
                        return
                except curio.TaskTimeout:
                    pass
        finally:
            self.state = 'finished'

    def cancel(self):
        self.cancel_event.set()


class Daemon:

    def __init__(self):
        self.runner_count = 0
        self.runners = {}

    def clean_runners(self):
        """ Check for any items in self.runners that have finished and delete them """
        for key in list(self.runners.keys()):
            if self.runners[key].state != 'running':
                del self.runners[key]

    async def process_start(self, job_name):
        self.clean_runners()
        if job_name in self.runners:
            print("Job with name {} already running".format(job_name))
            return
        print("starting job: {} (runner count {})".format(job_name, self.runner_count))
        self.runners[job_name] = Runner(self.runner_count, job_name)
        await self.task_group.spawn(self.runners[job_name].run)
        self.runner_count += 1

    async def process_status(self):
        self.clean_runners()
        print("status is ...")
        # import pdb; pdb.set_trace()
        for runner in self.runners.values():
            print("  {} is running".format(runner.xyz))
        print()

    async def process_kill(self, job_name):
        self.clean_runners()
        if job_name not in self.runners:
            print("Job {} not running!".format(job_name))
            return
        print("killing job: {}".format(job_name))
        self.runners[job_name].cancel()

    async def process_stop(self):
        print("stop daemon and exit")
        await self.task_group.cancel_remaining()
        raise StopDaemon()

    @property
    def command_processors(self):
        return {
            "start": self.process_start,
            "status": self.process_status,
            "kill": self.process_kill,
            "stop": self.process_stop,
        }

    async def process_command(self, command):
        command_words = command.strip().split()
        if len(command_words) == 0:
            return
        first_word = command_words[0]
        if first_word not in self.command_processors:
            raise InvalidCommandError("Invalid command: {}".format(first_word))
        await self.command_processors[first_word](*command_words[1:])

    async def main(self, argv):
        async with curio.TaskGroup() as self.task_group:
            while True:
                try:
                    command = await curio.run_in_thread(input, "Enter command: ")
                except EOFError:
                    command = "stop"
                try:
                    await self.process_command(command)
                except InvalidCommandError as error:
                    print("Invalid command: {}".format(error))
                except StopDaemon:
                    break
        return 0


def main(argv):
    daemon = Daemon()
    return curio.run(daemon.main, argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
