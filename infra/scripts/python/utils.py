import subprocess


class OSUtils:
    @staticmethod
    def run_command(command: list[str], check_output=False, shell=False, sudo=False, capture_output: bool = True):
        if sudo:
            command = ["sudo"] + command
        try:
            if check_output:
                result = subprocess.run(
                    command, check=True, capture_output=capture_output, text=True, shell=shell
                )
                return result.stdout.strip()
            else:
                subprocess.run(command, check=True, shell=shell)
        except subprocess.CalledProcessError:
            raise
        except FileNotFoundError:
            raise
