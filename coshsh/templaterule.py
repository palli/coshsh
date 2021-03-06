#!/usr/bin/env python
#-*- encoding: utf-8 -*-
#
# Copyright 2010-2012 Gerhard Lausser.
# This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

class TemplateRule:
    def __init__(self, needsattr=None, isattr=None, template=None, unique_attr="name", unique_config=None, self_name="application", suffix="cfg"):
        # This rule applies by default (needsattr=None) or if a certain
        # property exists
        self.needsattr = needsattr
        self.isattr = isattr
        self.template = template
        # Sometimes more than one configs are needed
        # This property is used to separate the application objects
        self.unique_attr = unique_attr 
        # The name of the config file which can contain %s
        self.unique_config = unique_config
        self.suffix = suffix
        self.self_name = self_name
    
    def __str__(self):
        return "Rule: needsattr=%s, isattr=%s, template=%s, unique_attr=%s, unique_config=%s, suffix=%s, self_name=%s" % (self.needsattr, self.isattr, self.template, self.unique_attr, self.unique_config, self.suffix, self.self_name)

