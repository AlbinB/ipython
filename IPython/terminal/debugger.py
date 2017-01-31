from IPython.core.debugger import Pdb

from IPython.core.completer import IPCompleter
from .ptutils import IPythonPTCompleter

from prompt_toolkit.token import Token
from prompt_toolkit.shortcuts import create_prompt_application
from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.enums import EditingMode
import sys


class TerminalPdb(Pdb):
    def __init__(self, *args, **kwargs):
        Pdb.__init__(self, *args, **kwargs)
        self._ptcomp = None
        self.pt_init()

    def pt_init(self):
        def get_prompt_tokens(cli):
            return [(Token.Prompt, self.prompt)]

        def patch_stdout(**kwargs):
            return self.pt_cli.patch_stdout_context(**kwargs)

        if self._ptcomp is None:
            compl = IPCompleter(shell=self.shell,
                                        namespace={},
                                        global_namespace={},
                                        parent=self.shell,
                                       )
            self._ptcomp = IPythonPTCompleter(compl, patch_stdout=patch_stdout)

        self._pt_app = create_prompt_application(
                            editing_mode=getattr(EditingMode, self.shell.editing_mode.upper()),
                            history=self.shell.debugger_history,
                            completer= self._ptcomp,
                            enable_history_search=True,
                            mouse_support=self.shell.mouse_support,
                            get_prompt_tokens=get_prompt_tokens
        )
        self.pt_cli = CommandLineInterface(self._pt_app, eventloop=self.shell._eventloop)

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.

        override the same methods from cmd.Cmd to provide prompt toolkit replacement.
        """
        if not self.use_rawinput:
            raise ValueError('Sorry ipdb does not support use_rawinput=False')

        self.preloop()

        try:
            if intro is not None:
                self.intro = intro
            if self.intro:
                self.stdout.write(str(self.intro)+"\n")
            stop = None
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    self._ptcomp.ipy_completer.namespace = self.curframe_locals
                    self._ptcomp.ipy_completer.global_namespace = self.curframe.f_globals
                    try:
                        line = self.pt_cli.run(reset_current_buffer=True).text
                    except EOFError:
                        line = 'EOF'
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
            self.postloop()
        except Exception:
            raise


def set_trace(frame=None):
    """
    Start debugging from `frame`.

    If frame is not specified, debugging starts from caller's frame.
    """
    TerminalPdb().set_trace(frame or sys._getframe().f_back)


if __name__ == '__main__':
    import pdb
    # IPython.core.debugger.Pdb.trace_dispatch shall not catch
    # bdb.BdbQuit. When started through __main__ and an exception
    # happened after hitting "c", this is needed in order to
    # be able to quit the debugging session (see #9950).
    old_trace_dispatch = pdb.Pdb.trace_dispatch
    pdb.Pdb = TerminalPdb
    pdb.Pdb.trace_dispatch = old_trace_dispatch
    pdb.main()
