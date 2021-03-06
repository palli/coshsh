# -*- coding: utf-8 -*-

import os
import logging
from item import Item
from templaterule import TemplateRule

logger = logging.getLogger('coshsh')

translations = (
    (u'\N{LATIN SMALL LETTER SHARP S}', u'ss'),
    (u'\N{LATIN SMALL LETTER O WITH DIAERESIS}', u'oe'),
    (u'\N{LATIN SMALL LETTER U WITH DIAERESIS}', u'ue'),
    (u'\N{LATIN CAPITAL LETTER A WITH DIAERESIS}', u'Ae'),
    (u'\N{LATIN CAPITAL LETTER O WITH DIAERESIS}', u'Oe'),
    (u'\N{LATIN CAPITAL LETTER U WITH DIAERESIS}', u'Ue'),
    # et cetera
)


class Contact(Item):

    id = 1 #0 is reserved for host (primary node for parents)
    my_type = 'contact'
    app_template = "app.tpl"

    template_rules = [
        TemplateRule(
            template="contact",
            self_name="contact",
            unique_attr="contact_name", unique_config="contact_%s",
        )
    ]

    def __init__(self, params={}):
        self.email = None
        self.pager = None
        self.address1 = None
        self.address2 = None
        self.address3 = None
        self.address4 = None
        self.address5 = None
        self.address6 = None
        self.can_submit_commands = False
        self.contactgroups = []
        super(Contact, self).__init__(params)
        self.fingerprint = lambda s=self:s.__class__.fingerprint(params)
        if not hasattr(self, 'host_notification_period'):
            self.host_notification_period = self.notification_period
        if not hasattr(self, 'service_notification_period'):
            self.service_notification_period = self.notification_period
        try:
            for from_str, to_str in translations:
                self.name = self.name.replace(from_str, to_str)
            if self.type.startswith("WEB"):
                self.contact_name = self.userid
                if self.type == "WEBREADWRITE":
                    self.can_submit_commands = True
                self.service_notification_options = "n"
                self.host_notification_options = "n"
                self.service_notification_commands = ["notify_by_nothing"]
                self.host_notification_commands = ["notify_by_nothing"]
            elif self.type == "SMS":
                self.contact_name = "sms_" + self.name + "_" + self.notification_period.replace("/", "_")
                self.pager = self.address
                self.service_notification_options = "w,c,u"
                self.host_notification_options = "d,u"
                self.service_notification_commands = ["notify_by_nothing"] #changeme
                self.host_notification_commands = ["notify_by_nothing"]
            elif self.type == "PHONE":
                self.contact_name = "phone_" + self.name + "_" + self.notification_period.replace("/", "_")
                self.pager = self.address
            elif self.type == "MAIL":
                self.contact_name = "mail_" + self.name + "_" + self.notification_period.replace("/", "_")
                self.email = self.address
                if not hasattr(self, "service_notification_options"):
                    setattr(self, "service_notification_options", "w,c,u,r,f,s")
                if not hasattr(self, "host_notification_options"):
                    setattr(self, "host_notification_options", "d,u,r,f,s")
                self.service_notification_commands = ["service-notify-by-email"]
                self.host_notification_commands = ["host-notify-by-email"]
            else:
                self.contact_name = "unknown_" + self.name + "_" + self.notification_period.replace("/", "_")
        except Exception:
            self.contact_name = "failed_user"
            raise


    @classmethod
    def fingerprint(self, params):
        if params["type"] and params["type"].startswith("WEB"):
            return "+".join([unicode(params.get(a, "")) for a in ["name", "type", "address", "userid"]])
        else:
            return "+".join([unicode(params.get(a, "")) for a in ["name", "type", "address", "userid", "notification_period"]])


    def __str__(self):
        fipri = " ".join([unicode(getattr(self, a, "")) for a in ["name", "type", "address", "userid"]])
        grps = ",".join(self.contactgroups)
        return unicode("contact %s groups (%s)" % (fipri, grps))


