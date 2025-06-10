import fabric.functions as fn
import logging
import sys

from argparse import Namespace
from fabric_cli.commands.auth import fab_auth
from fabric_cli.commands.config import fab_config
from fabric_cli.commands.jobs import fab_jobs

udf = fn.UserDataFunctions()

class StreamToLogger:
    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level
        self._buffer = ""

    def write(self, message):
        self._buffer += message
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip()
            if line:
                self.logger.log(self.level, line)

    def flush(self):
        if self._buffer:
            self.logger.log(self.level, self._buffer.rstrip())
            self._buffer = ""
            
    def isatty(self):
        return False

def capture_all_output():
    logger = logging.getLogger()
    sys.stdout = StreamToLogger(logger, logging.INFO)
    sys.stderr = StreamToLogger(logger, logging.ERROR)

@udf.function()
def run_job(workspacename: str, itemname: str, itemtype: str) -> str:
    logging.basicConfig(level=logging.INFO)
    capture_all_output()  # Log all prints and errors

    args = Namespace(
        command_path=["/"],
        path=["/"],
        command="config",
        config_command="set",
        key="encryption_fallback_enabled",
        value="true"
    )
    fab_config.set_config(args)

    args = Namespace(
        auth_command="login",
        username="**********",
        password="**********",
        tenant="**********",
        identity=None,
        federated_token=None,
        certificate=None
    )
    fab_auth.init(args)
    fab_auth.status(None)

    args = Namespace(
        command_path=["/"],
        command="job",
        jobs_command="run",
        path=[f"{workspacename}.Workspace/{itemname}.{itemtype}"]
    )
    fab_jobs.run_command(args)

    return f"Job trigger function executed for {itemtype} {itemname} in workspace {workspacename}"
