import os
from item import Item
from templaterule import TemplateRule

class Host(Item):

    id = 1 #0 is reserved for host (primary node for parents)
    template_rules = [
        TemplateRule(needsattr=None, 
            template="host", 
            self_name="host",
        ),
    ]
    lower_columns = ['address', 'type', 'os', 'hardware', 'virtual', 'location', 'department']

    def __init__(self, params={}):
        for c in self.__class__.lower_columns:
            try:
                params[c] = params[c].lower()
            except Exception:
                if c in params:
                    params[c] = None
        self.hostgroups = []
        self.contacts = []
        self.contact_groups = []
        self.templates = []
        self.ports = [22] # can be changed with a PORT detail
        super(Host, self).__init__(params)
        self.alias = getattr(self, 'alias', self.host_name)
        self.fingerprint = lambda s=self:s.__class__.fingerprint(params)

    @classmethod
    def fingerprint(self, params):
        return "%s" % (params["host_name"], )

    def is_correct(self):
        return hasattr(self.host_name) and self.host_name != None

    def create_hostgroups(self):
        pass

    def create_contacts(self):
        pass

    def create_templates(self):
        pass

