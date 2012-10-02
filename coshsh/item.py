#!/usr/bin/env python
#-*- encoding: utf-8 -*-
#
# Copyright 2010-2012 Gerhard Lausser.
# This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
import re
import locale
from jinja2 import FileSystemLoader, Environment, TemplateSyntaxError, TemplateNotFound
from copy import copy, deepcopy
from log import logger


class EmptyObject(object):
    pass


class Item(object):
    template_cache = {}

    @classmethod
    def reload_template_path(cls):
        loader = FileSystemLoader(cls.templates_path)
        cls.env = Environment(loader=loader)
        cls.env.trim_blocks = True

    def __init__(self, params={}):
        #print "Item.__init__(", self.__class__.__name__
        cls = self.__class__
        self.id = cls.id
        cls.id += 1

        self.log = logger

        for key in params:
            #print "set key", self.__class__.__name__, key
            setattr(self, key, params[key])

        if not hasattr(self, "monitoring_details"):
            # if not pre-set through the class
            self.monitoring_details = []
        else:
            setattr(self, "monitoring_details", list(self.__class__.monitoring_details))
        self.config_files = {}


    def clone(self):
        """ Return a copy of the item, but give him a new id """
        cls = self.__class__
        i = cls({})# Dummy item but with it's own running properties
        save_id = i.id
        new_obj = copy(self)
        new_obj.id = save_id
        return new_obj


    def write_config(self, target_dir):
        my_target_dir = os.path.join(target_dir, "hosts", self.host_name)
        for file in self.config_files:
            content = self.config_files[file]
            with open(os.path.join(my_target_dir, file), "w") as f:
                f.write(content)


    def resolve_monitoring_details(self):
        details = [d for d in self.monitoring_details]
        for detail in details:
            property = detail.__class__.property
            if property == "generic":
                if detail.__class__.property_type == dict:
                    for key in detail.dictionary:
                        if key:
                            if ":" in key:
                                dictname, key = key.split(":")
                                try:
                                    setattr(getattr(self, dictname), key, detail.dictionary[dictname + ":" + key])
                                except Exception:
                                    setattr(self, dictname, EmptyObject())
                                    setattr(getattr(self, dictname), key, detail.dictionary[dictname + ":" + key])
                            else:
                                setattr(self, key, detail.dictionary[key])
                else:
                    setattr(self, detail.attribute, detail.value)
            else:
                if detail.__class__.property_type == list:
                    if not hasattr(self, property):
                        setattr(self, property, [])
                    if hasattr(detail.__class__, "unique_attribute"):
                        # from the details remove an existing detail
                        # - which is of this class
                        # - which has the same unique_attr
                        if [o for o in getattr(self, property) if o.__class__ == detail.__class__ and getattr(o, detail.__class__.unique_attribute) == getattr(detail, detail.__class__.unique_attribute)]:
                            old = getattr(self, property)
                            new = [o for o in old if ((o.__class__ != detail.__class__) or (getattr(o, detail.__class__.unique_attribute) != getattr(detail, detail.__class__.unique_attribute)))]
                            new.append(detail)
                            setattr(self, property, new)
                        #print "res", self.host.host_name, detail.path
                        else:
                            getattr(self, property).append(detail)
                    else:
                        if hasattr(detail.__class__, "property_attr"):
                            getattr(self, property).append(getattr(detail, getattr(detail.__class__, "property_attr")))
                        else:
                            getattr(self, property).append(detail)
                else:
                    if getattr(detail.__class__, 'property_flat', False):
                        # ex. MonitoringDetailRole: appl.role == str instead of appl.role.role == str
                        setattr(self, property, getattr(detail, property))
                    else:
                        setattr(self, property, detail)
            # This detail has been resolved. Maybe we run resolve_monitoring_details
            # later again, we don't want to repeat ourselves.
            self.monitoring_details.remove(detail)
        if details:
            self.wemustrepeat()

    def wemustrepeat(self):
        """
        This method is called by some classes if different monitoring_details need to interact.
        Ex. (username/password was set in a LOGIN detail and/or a URL detail
        """
        pass

    def pythonize(self):
        if hasattr(self, "templates"):
            self.templates = self.templates.split(',')
        if hasattr(self, "contactgroups"):
            self.contactgroups = self.contactgroups.split(',')
        if hasattr(self, "contact_groups"): #! contacts have contact!_!groups
            self.contact_groups = self.contact_groups.split(',')
        if hasattr(self, "contacts"):
            self.contacts = self.contacts.split(',')
        if hasattr(self, "hostgroups"):
            self.hostgroups = self.hostgroups.split(',')
        if hasattr(self, "servicegroups"):
            self.servicegroups = self.servicegroups.split(',')
        if hasattr(self, "members"):
            self.members = self.members.split(',')
        if hasattr(self, "parents"):
            self.parents = self.parents.split(',')
        if hasattr(self, "host_notification_commands"):
            self.host_notification_commands = self.host_notification_commands.split(',')
        if hasattr(self, "service_notification_commands"):
            self.service_notification_commands = self.service_notification_commands.split(',')


    def depythonize(self):
        if hasattr(self, "templates"):
            self.templates = ",".join(sorted(self.templates, cmp=locale.strcoll))
        if hasattr(self, "contactgroups"):
            self.contactgroups = ",".join(sorted(self.contactgroups, cmp=locale.strcoll))
        if hasattr(self, "contact_groups"):
            self.contact_groups = ",".join(sorted(self.contact_groups, cmp=locale.strcoll))
        if hasattr(self, "contacts"):
            self.contacts = ",".join(sorted(self.contacts, cmp=locale.strcoll))
        if hasattr(self, "hostgroups"):
            self.hostgroups = ",".join(sorted(self.hostgroups, cmp=locale.strcoll))
        if hasattr(self, "servicegroups"):
            self.servicegroups = ",".join(sorted(self.servicegroups, cmp=locale.strcoll))
        if hasattr(self, "members"):
            self.members = ",".join(sorted(self.members, cmp=locale.strcoll))
        if hasattr(self, "parents"):
            self.parents = ",".join(sorted(self.parents, cmp=locale.strcoll))
        if hasattr(self, "host_notification_commands"):
            self.host_notification_commands = ",".join(sorted(self.host_notification_commands, cmp=locale.strcoll))
        if hasattr(self, "service_notification_commands"):
            self.service_notification_commands = ",".join(sorted(self.service_notification_commands, cmp=locale.strcoll))


    def load_cfg_template_cache(self, template_cache, jinja2):
        if hasattr(self.__class__, "template_rules"):
            for rule in self.template_rules:
                try:
                    if not rule.template in template_cache:
                        template_cache[rule.template] = jinja2.env.get_template(rule.template + ".tpl")
                        logger.info("load template " + rule.template)
                except TemplateSyntaxError as e:
                    logger.critical("%s template %s has an error in line %d: %s" % (self.__class__.__name__, rule.template, e.lineno, e.message))
                except TemplateNotFound:
                    logger.error("cannot find template " + rule.template)
                except Exception as exp:
                    logger.critical("error in template %s (%s,%s)" (rule.template, exp.__class__.__name__, exp))


    def render_cfg_template(self, template_cache, name, output_name, **kwargs):
        if name in template_cache:
            # transform hostgroups, contacts, etc. from list to string
            self.depythonize()
            try:
                self.config_files[output_name + ".cfg"] = template_cache[name].render(kwargs)
            except Exception as exp:
                logger.critical("render exception in template %s for %s: %s" % (name, self, exp))
            # transform hostgroups, contacts, etc. back to lists
            self.pythonize()


    def render(self, template_cache, jinja2):
        self.load_cfg_template_cache(template_cache, jinja2)
        for rule in self.template_rules:
            render_this = False
            if not rule.needsattr:
                # TemplateRule(template="os_solaris_default")
                render_this = True

            elif (hasattr(self, rule.needsattr) and rule.isattr == None):
                # TemplateRule(needsattr=None,template="os_solaris_default")
                render_this = True

            elif hasattr(self, rule.needsattr) and not isinstance (getattr(self, rule.needsattr), list) and ((getattr(self, rule.needsattr) == rule.isattr) or re.match(rule.isattr, getattr(self, rule.needsattr))):
                # TemplateRule(needsattr="cluster", isattr="veritas",
                #     template="os_solaris_cluster_veritas")
                render_this = True

            elif hasattr(self, rule.needsattr) and isinstance (getattr(self, rule.needsattr), list) and [elem for elem in getattr(self, rule.needsattr) if (elem == rule.isattr or re.match(rule.isattr, elem))]:
                # TemplateRule(needsattr="hostgroups",
                #     isattr="cluster_solaris_veritas.*",
                #     template="os_solaris_cluster_veritas")
                render_this = True
                
            elif hasattr(self, rule.needsattr) and isinstance (getattr(self, rule.needsattr), list):
                pass

            if render_this:
                if rule.unique_config and hasattr(self, rule.unique_attr):
                    self.render_cfg_template(template_cache, rule.template, rule.unique_config % getattr(self, rule.unique_attr), **dict([(rule.self_name, self)]))
                else:
                    self.render_cfg_template(template_cache, rule.template, rule.template, **dict([(rule.self_name, self)]))
