import sublime

from LSP.plugin import AbstractPlugin


class Vibescript(AbstractPlugin):
    @classmethod
    def name(cls):
        return "vibescript"

    @classmethod
    def configuration(cls):
        basename = "LSP-vibescript.sublime-settings"
        package_name = __package__.split(".")[0]
        return sublime.load_settings(basename), "Packages/{}/{}".format(package_name, basename)
