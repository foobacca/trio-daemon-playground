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

import trio


SLEEP_TIME = 5


class StopDaemon(Exception):
    pass


class InvalidCommandError(Exception):
    pass


async def runner(runner_count, xyz, cancel_event):
    """
    print every 10 seconds for 5 minutes
    """
    for iter_count in range(300//SLEEP_TIME):
        if cancel_event.is_set():
            return
        print('runner number {}, count {}: {}'.format(runner_count, iter_count, xyz))
        with trio.move_on_after(SLEEP_TIME):
            await cancel_event.wait()
            print("I've been killed ({}).".format(xyz))


class Daemon:

    def __init__(self):
        self.runner_count = 0
        self.runners = {}

    def clean_runners(self):
        """ Check for any items in self.runners that have finished and delete them """
        running_task_names = [t.name for t in self.nursery.child_tasks]
        for key in list(self.runners.keys()):
            if key not in running_task_names:
                del self.runners[key]

    def process_start(self, job_name):
        self.clean_runners()
        if job_name in self.runners:
            print('Job with name {} already running'.format(job_name))
            return
        print('starting job: {} (runner count {})'.format(job_name, self.runner_count))
        self.runners[job_name] = {
            'count': self.runner_count,
            'cancel': trio.Event()
        }
        self.nursery.start_soon(runner, self.runner_count, job_name, self.runners[job_name]['cancel'], name=job_name)
        self.runner_count += 1

    def process_status(self):
        self.clean_runners()
        print('status is ...')
        for task in self.nursery.child_tasks:
            print('  {} is running'.format(task.name))
        print()

    def process_kill(self, job_name):
        self.clean_runners()
        if job_name not in self.runners:
            print('Job {} not running!'.format(job_name))
            return
        print('killing job: {}'.format(job_name))
        self.runners[job_name]['cancel'].set()

    def process_stop(self):
        print('stop daemon and exit')
        self.nursery.cancel_scope.cancel()
        raise StopDaemon()

    @property
    def command_processors(self):
        return {
            'start': self.process_start,
            'status': self.process_status,
            'kill': self.process_kill,
            'stop': self.process_stop
        }

    def process_command(self, command):
        command_words = command.strip().split()
        if len(command_words) == 0:
            return
        first_word = command_words[0]
        if first_word not in self.command_processors:
            raise InvalidCommandError('Invalid command: {}'.format(first_word))
        self.command_processors[first_word](*command_words[1:])

    async def main(self, argv):
        async with trio.open_nursery() as self.nursery:
            while True:
                try:
                    command = await trio.run_sync_in_worker_thread(input, 'Enter command: ')
                except EOFError:
                    command = 'stop'
                try:
                    self.process_command(command)
                except InvalidCommandError as error:
                    print('Invalid command: {}'.format(error))
                except StopDaemon:
                    break
        return 0


def main(argv):
    daemon = Daemon()
    return trio.run(daemon.main, argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
