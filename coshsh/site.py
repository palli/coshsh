#!/usr/bin/env python
#-*- encoding: utf-8 -*-
#
# Copyright 2010-2012 Gerhard Lausser.
# This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import sys
import os
import re
import shutil
import inspect
import time
from subprocess import Popen, PIPE, STDOUT
from coshsh.log import logger
from coshsh.item import Item
from monitoring_detail import MonitoringDetail
from application import Application
from datasource import Datasource

class Site(object):

    def __init__(self, **kwargs):
        self.name = kwargs["name"]
        logger.info("site %s init" % self.name)
        self.objects_dir = kwargs["objects_dir"]
        self.templates_dir = kwargs.get("templates_dir", os.path.join(os.path.dirname(__file__), '../sites/default/templates'))
        self.classes_dir = kwargs.get("classes_dir", os.path.join(os.path.dirname(__file__), '../sites/default/classes'))
        self.filter = kwargs.get("filter")
        self.default_classes_dir = os.path.join(os.path.dirname(__file__), '../sites/default/classes')
        if self.templates_dir:
            Item.templates_path.insert(0, self.templates_dir)
            Item.reload_template_path()
            logger.debug("Item.templates_path reloaded %s" % Item.templates_path)
        logger.info("site %s objects_dir %s" % (self.name, os.path.abspath(self.objects_dir)))
        logger.info("site %s classes_dir %s" % (self.name, os.path.abspath(self.classes_dir)))
        logger.info("site %s templates_dir %s" % (self.name, os.path.abspath(self.templates_dir)))

        self.datasources = []

        self.hosts = {}
        self.applications = {}
        self.appdetails = {}
        self.contacts = {}
        self.contactgroups = {}
        self.dependencies = {}
        self.bps = {}

        self.hostgroups = {}

        self.datasource_filters = {}
        if kwargs.get("filter"):
            for rule in kwargs.get("filter").split(','):
                match = re.match(r'(\w+)\((.*)\)', rule)
                if match:
                    self.datasource_filters[match.groups()[0].lower()] = match.groups()[1]
        self.static_dir = os.path.join(self.objects_dir, 'static')
        self.dynamic_dir = os.path.join(self.objects_dir, 'dynamic')
        self.init_class_cache()


    def prepare_target_dir(self):
        logger.info("site %s dynamic_dir %s" % (self.name, self.dynamic_dir))
        if not os.path.exists(self.dynamic_dir):
            # will not have been removed with a .git inside
            os.mkdir(self.dynamic_dir)
        os.mkdir(os.path.join(self.dynamic_dir, 'hosts'))
        os.mkdir(os.path.join(self.dynamic_dir, 'hostgroups'))


    def cleanup_target_dir(self):
        if os.path.isdir(self.dynamic_dir):
            try:
                if os.path.exists(self.dynamic_dir + "/.git"):
                    for subdir in [sd for sd in os.listdir(self.dynamic_dir) if sd != ".git"]:
                        logger.info("site %s remove dynamic_dir %s" % (self.name, self.dynamic_dir + "/" + subdir))
                        shutil.rmtree(self.dynamic_dir + "/" + subdir)
                else:
                    logger.info("site %s remove dynamic_dir %s" % (self.name, self.dynamic_dir))
                    shutil.rmtree(self.dynamic_dir)
            except Exception as e:
                logger.info("site %s has problems with dynamic_dir %s" % (self.name, self.dynamic_dir))
                logger.info(e)
                raise e
        else:
            logger.info("site %s dynamic_dir %s does not exist" % (self.name, self.dynamic_dir))


    def count_before_objects(self):
        try:
            hosts = len([name for name in os.listdir(os.path.join(self.dynamic_dir, 'hosts')) if os.path.isdir(os.path.join(self.dynamic_dir, 'hosts', name))])
            apps = len([app for host in os.listdir(os.path.join(self.dynamic_dir, 'hosts')) if os.path.isdir(os.path.join(self.dynamic_dir, 'hosts', host)) for app in os.listdir(os.path.join(self.dynamic_dir, 'hosts', host)) if app != 'host.cfg'])
            self.old_objects = (hosts, apps)
        except Exception:
            self.old_objects = (0, 0)

    def count_after_objects(self):
        if os.path.isdir(self.dynamic_dir):
            hosts = len([name for name in os.listdir(os.path.join(self.dynamic_dir, 'hosts')) if os.path.isdir(os.path.join(self.dynamic_dir, 'hosts', name))])
            apps = len([app for host in os.listdir(os.path.join(self.dynamic_dir, 'hosts')) if os.path.isdir(os.path.join(self.dynamic_dir, 'hosts', host)) for app in os.listdir(os.path.join(self.dynamic_dir, 'hosts', host)) if app != 'host.cfg'])
            self.new_objects = (hosts, apps)
        else:
            self.new_objects = (0, 0)

    def collect(self):
        for ds in self.datasources:
            filter = self.datasource_filters.get(ds.name)
            hosts, applications, contacts, contactgroups, appdetails, dependencies, bps = ds.read(filter=filter, intermediate_hosts=self.hosts, intermediate_applications=self.applications)
            logger.info("site %s read from datasource %s %d hosts, %d applications, %d details, %d contacts, %d dependencies, %d business processes" % (self.name, ds.name, len(hosts), len(applications), len(appdetails), len(contacts), len(dependencies), len(bps)))
            
            for host in hosts:
                self.hosts[host.host_name] = host
            for app in applications:
                self.applications[app.fingerprint()] = app
            for cg in contactgroups:
                self.contactgroups[cg.contactgroup_name] = cg
            for c in contacts:
                self.contacts[c.fingerprint()] = c

        for host in self.hosts.values():
            host.resolve_monitoring_details()
            host.create_templates()
            host.create_hostgroups()
            host.create_contacts()
            for hostgroup in host.hostgroups:
                try:
                    self.hostgroups[hostgroup].append(host.host_name)
                except Exception:
                    self.hostgroups[hostgroup] = []
                    self.hostgroups[hostgroup].append(host.host_name)

        orphaned_applications = []
        for app in self.applications.values():
            try:
                setattr(app, 'host', self.hosts[app.host_name])
                app.resolve_monitoring_details()
                app.create_templates()
                app.create_servicegroups()
                app.create_contacts()
            except KeyError:
                logger.info("application %s %s refers to non-existing host %s" % (app.name, app.type, app.host_name))
                orphaned_applications.append(app.fingerprint())
        for oa in orphaned_applications:
            del self.applications[oa]

        from hostgroup import Hostgroup
        for (hostgroup_name, members) in self.hostgroups.items():
            logger.debug("creating hostgroup %s" % hostgroup_name)
            self.hostgroups[hostgroup_name] = Hostgroup({ "hostgroup_name" : hostgroup_name, "members" : members})
            self.hostgroups[hostgroup_name].create_templates()
            self.hostgroups[hostgroup_name].create_contacts()
 

    def render(self):
        for host in self.hosts.values():
            host.env.loader.searchpath = Item.env.loader.searchpath
            host.render()
        for app in self.applications.values():
            # because of this __new__ construct the Item.searchpath is
            # not inherited. Needs to be done explicitely
            app.env.loader.searchpath = Item.env.loader.searchpath
            app.render()
        for cg in self.contactgroups.values():
            cg.render()
        for c in self.contacts.values():
            c.render()
        for hg in self.hostgroups.values():
            hg.render()
        if self.classes_dir:
            Item.reload_template_path()
            


    def output(self):
        print self.old_objects
        delta_hosts, delta_services = 0, 0
        for hostgroup in self.hostgroups.values():
            hostgroup.write_config(self.dynamic_dir)
        for host in self.hosts.values():
            host.write_config(self.dynamic_dir)
        for app in self.applications.values():
            app.write_config(self.dynamic_dir)
        for cg in self.contactgroups.values():
            cg.write_config(self.dynamic_dir)
        for c in self.contacts.values():
            c.write_config(self.dynamic_dir)
        self.count_after_objects()
        try:
            delta_hosts = 100 * abs(self.new_objects[0] - self.old_objects[0]) / self.old_objects[0]
            delta_services = 100 * abs(self.new_objects[1] - self.old_objects[1]) / self.old_objects[1]
        except Exception, e:
            #print e
            # if there are no objects in the dyndir yet, this results in a
            # division by zero
            pass

        logger.info("number of files before: %d hosts, %d applications" % self.old_objects)
        logger.info("number of files after:  %d hosts, %d applications" % self.new_objects)
        if delta_hosts > 10 or delta_services > 10:
            print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            print "number of hosts changed by %.2f percent" % delta_hosts
            print "number of applications changed by %.2f percent" % delta_services
            print "please check your datasource before activating this config."
            print "if you use a git repository, you can go back to the last"
            print "valid configuration with the following commands:"
            print "cd %s" % self.dynamic_dir
            print "git reset --hard"
            print "git checkout ."
            print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        
        elif os.path.exists(self.dynamic_dir + '/.git'):
            logger.debug("dynamic_dir is a git repository")
        
            save_dir = os.getcwd()
            os.chdir(self.dynamic_dir)
            print "git add------------------"
            process = Popen(["git", "add", "."], stdout=PIPE, stderr=STDOUT)
            output, unused_err = process.communicate()
            retcode = process.poll()
            print output 
            commitmsg = time.strftime("%Y-%m-%d-%H-%M-%S") + " %d hostfiles,%d appfiles" % (self.new_objects[0], self.new_objects[1])
            print "git commit------------------"
            print "commit-comment", commitmsg
            process = Popen(["git", "commit", "-a", "-m", commitmsg], stdout=PIPE, stderr=STDOUT)
            output, unused_err = process.communicate()
            retcode = process.poll()
            print output 
            os.chdir(save_dir)
            self.analyze_output(output)

    def analyze_output(self, output):
        add_hosts = []
        del_hosts = []
        for line in output.split("\n"):
            #create mode 100644 hosts/libmbp1.naxgroup.net/host.cfg
            match = re.match(r'\s*create mode.*hosts/(.*)/host.cfg', line)
            if match:
                add_hosts.append(match.group(1))
            #delete mode 100644 hosts/litxd01.emea.gdc/host.cfg
            match = re.match(r'\s*delete mode.*hosts/(.*)/host.cfg', line)
            if match:
                del_hosts.append(match.group(1))
        if add_hosts:
            logger.info("add hosts: %s" % ','.join(add_hosts))
        if del_hosts:
            logger.info("del hosts: %s" % ','.join(del_hosts))

    def read(self):
        return self.hosts.values(), self.applications.values(), self.appdetails, self.contacts, self.dependencies, self.bps


    def init_class_cache(self):
        class_factory = []
        detail_factory = []
        datasource_factory = []
        if self.classes_dir != self.default_classes_dir:
            sys.path.insert(0, self.default_classes_dir)
            sys.path.insert(0, self.classes_dir)
        else:
            sys.path.insert(0, self.default_classes_dir)
        logger.debug("site %s init detail cache" % self.name)
        for module in  [item for sublist in [os.listdir(p) for p in sys.path[1], sys.path[0] if os.path.exists(p) and os.path.isdir(p)] for item in sublist if item[-3:] == ".py" and item.startswith("detail_")]:
            toplevel = __import__(module[:-3], locals(), globals())
            for cl in inspect.getmembers(toplevel, inspect.isfunction):
                if cl[0] ==  "__detail_ident__":
                    detail_factory.append(cl[1])
        MonitoringDetail.detail_factory = detail_factory
        # find monitoring item files which have the ability
        # to identify themselves with a __mi_ident__ finction
        logger.debug("site %s init class cache" % self.name)
        for module in  [item for sublist in [os.listdir(p) for p in sys.path[1], sys.path[0] if os.path.exists(p) and os.path.isdir(p)] for item in sublist if item[-3:] == ".py"]:
            toplevel = __import__(module[:-3], locals(), globals())
            for cl in inspect.getmembers(toplevel, inspect.isfunction):
                if cl[0] ==  "__mi_ident__":
                    class_factory.append(cl[1])
        Application.class_factory = class_factory
        # find datasource adapter files which have the ability
        # to identify themselves with a __ds_ident__ finction
        logger.debug("site %s init datasource cache" % self.name)
        for module in  [item for sublist in [os.listdir(p) for p in sys.path[1], sys.path[0] if os.path.exists(p) and os.path.isdir(p)] for item in sublist if item[-3:] == ".py" and item.startswith("datasource_")]:
            try:
                # maybe module was already loaded by another site
                # and another path
                del sys.modules[module.replace(".py", "")]
            except Exception as exp:
                pass
            toplevel = __import__(module[:-3], locals(), globals())
            for cl in inspect.getmembers(toplevel, inspect.isfunction):
                if cl[0] ==  "__ds_ident__":
                    datasource_factory.append(cl[1])
        Datasource.class_factory = datasource_factory
        if self.classes_dir != self.default_classes_dir:
            sys.path.remove(self.classes_dir)
            sys.path.remove(self.default_classes_dir)
        else:
            sys.path.remove(self.default_classes_dir)

    def add_datasource(self, **kwargs):
        newcls = Datasource.get_class(kwargs)
        if newcls:
            self.datasources.append(newcls(**kwargs))


