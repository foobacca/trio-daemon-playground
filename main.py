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


class StopDaemon(Exception):
    pass


class InvalidCommandError(Exception):
    pass


class Daemon(object):

    def process_start(self, job_name):
        print('starting job: {}'.format(job_name))

    def process_status(self):
        print('status is ...')

    def process_kill(self, job_name):
        print('killing job: {}'.format(job_name))

    def process_stop(self):
        print('stop daemon and exit')
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
            raise InvalidCommandError('empty command')
        first_word = command_words[0]
        if first_word not in self.command_processors:
            raise InvalidCommandError('Invalid command: {}'.format(first_word))
        self.command_processors[first_word](*command_words[1:])

    def main(self, argv):
        while True:
            command = input('Enter command: ')
            try:
                self.process_command(command)
            except InvalidCommandError as error:
                print('Invalid command: {}'.format(error))
            except StopDaemon:
                break
        return 0


def main(argv):
    daemon = Daemon()
    return daemon.main(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
