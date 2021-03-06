from application import Application
from templaterule import TemplateRule
from util import compare_attr

def __mi_ident__(params={}):
    if compare_attr("type", params, ".*red\s*hat.*|.*sles.*|.*linux.*|.*limux.*|.*debian.*|.*ubuntu.*|.*centos.*"):
        return Linux


class Linux(Application):
    template_rules = [
        TemplateRule(needsattr=None, 
            template="os_linux_default"),
        TemplateRule(needsattr="filesystems", 
            template="os_linux_fs"),
    ]

