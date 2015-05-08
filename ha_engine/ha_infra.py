import logging
import sys
from prettytable import PrettyTable
import pprint
import collections
from ssh.sshutils import SSH
import subprocess
import time
import re
import ha_parser
import os
from fpdb import  ForkedPdb as fdb
import paramiko

LOG_NAME = 'HA_AUTOMATION_INFRA'
DEBUG = False

# --- begin "pretty"
#
# pretty - A miniature library that provides a Python print and stdout
# wrapper that makes colored terminal text easier to use (e.g. without
# having to mess around with ANSI escape sequences). This code is public
# domain - there is no license except that you must leave this header.
#
# Copyright (C) 2008 Brian Nez <thedude at bri1 dot com>
#
# http://nezzen.net/2008/06/23/colored-text-in-python-using-ansi-escape-sequences/

codeCodes = {
    'black':     '0;30', 'bright gray':    '0;37',
    'blue':      '0;34', 'white':          '1;37',
    'green':     '0;32', 'bright blue':    '1;34',
    'cyan':      '0;36', 'bright green':   '1;32',
    'red':       '0;31', 'bright cyan':    '1;36',
    'purple':    '0;35', 'bright red':     '1;31',
    'yellow':    '0;33', 'bright purple':  '1;35',
    'dark gray': '1;30', 'bright yellow':  '1;33',
    'normal':    '0'
}


def stringc(text, color):
    """String in color."""
    return "\033[" + codeCodes[color] + "m" + text + "\033[0m"

# --- end "pretty"



ha_infra_report_tables = {}
ha_infra_historical_tables = {}

class NotifyNotImplemented(Exception):
    pass

def ha_logging(name):
    '''
    Initializing logger
    '''
    if name == None:
        name = LOG_NAME

    LOG = logging.getLogger(name)
    LOG.setLevel(logging.INFO)
    LOG.setLevel(logging.DEBUG)
    logHandler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - '
                                  '%(levelname)s - %(message)s')
    logHandler.setFormatter(formatter)
    LOG.addHandler(logHandler)
    return LOG

LOG = ha_logging(__name__)


def create_report_table(self, tablename, historical=False):

    if self:
        plugin = get_plugin_name(self)
    if tablename:
        plugin_table = ha_infra_report_tables.get(plugin, None)
        if historical:
            ha_infra_historical_tables[tablename] = True
        if plugin_table is None:
            ha_infra_report_tables[plugin] = [{tablename: []}]
        else:
            ha_infra_report_tables.get(plugin).append({tablename: []})


def add_table_headers(self, tablename, headers):
    if self:
        plugin = get_plugin_name(self)

    plugin_tables = ha_infra_report_tables.get(plugin)
    if plugin_tables:
        for table in plugin_tables:
            if tablename in table:
                if len(table.get(tablename)) > 0:
                    table.get(tablename)[0] = headers
                else:
                    table.get(tablename).append(headers)


def add_table_rows(self, tablename, rows):
    if self:
        plugin = get_plugin_name(self)
    plugin_tables = ha_infra_report_tables.get(plugin)
    if plugin_tables:
        for table in plugin_tables:
            if tablename in table:
                for row in rows:
                    table.get(tablename).append(row)


def display_infra_report(show_historical=False):
    ha_infra_repor = [ha_infra_report_tables]
    for plugin_tables in ha_infra_repor:
        for plugin_name in plugin_tables:
            for plugin_table in plugin_tables[plugin_name]:
                for tablename in plugin_table:
                    display = True
                    historic_table = ha_infra_historical_tables.get(tablename,
                                                                    False)
                    if historic_table and show_historical:
                        display = True
                    elif not historic_table and show_historical:
                        display = False
                    elif historic_table and not show_historical:
                        display = False
                    elif not historic_table and not show_historical:
                        display = True
                    if display:
                        individual_table = plugin_table[tablename]
                        headers = individual_table[0]
                        print
                        print "*"*15 + tablename + "*"*15
                        print "-" * (30 + len(tablename))
                        print
                        report_table = PrettyTable(headers)
                        for header in headers:
                           report_table.align[header] = "l"

                        report_table.padding_width = 3
                        rows = individual_table[1:]
                        for row in rows:
                            report_table.add_row(row)

                        print report_table


def display_report(module, steps=None):

    print '*' * 50
    if not steps:
        print '\t HA REPORT @ Final \t'
    else:
        print '\t HA REPORT @ ' + str(steps) + '\t'
    print '*' * 50

    if not module:
        LOG.critical('Nothing to report')
        return

    try:
        result =  module.display_report()
    except:
        LOG.info("ERROR while displaying report")

    header = result.get('headers', None)
    values = result.get('values', None)
    if header != None and values != None:
        print '-' * 50
        print 'Module:: %s ' %(module.__class__.__name__)
        print '_' * 50
        #print tabulate(result['values'], headers = result['headers'])
    else:
        LOG.critical('Unable to print report')
        ha_exit(0)

    print '*' * 50


def ha_exit(num):
    '''
    exit with num;
    '''
    if num == 0:
        sys.exit(num)

def wait_for_notification(sync):
    if sync:
        sync.wait()

def dump_on_console(info, title):
    print "---- " + title + " ---- "

    if info:
        pprint.pprint(info, indent=4)
    else:
            print " None"

    print "-------------------------"

def pretty(d, indent=0):
    for key, value in d.iteritems():
          print '\t' * indent + str(key)
          if isinstance(value, dict):
             pretty(value, indent+1)
          else:
             print '\t' * (indent+1) + str(value)

def get_subscribers_list():
    print "SUBSCRIBERS LIST"

def add_subscribers_for_module(subscriber_name, info):
    publishers = info.get('publishers', None)
    if not publishers:
        LOG.error("No Publishers found, Cannot subscribe")
        ha_exit(0)

    for publisher in publishers:
       print "%s subscribing to %s" % (subscriber_name, publisher)


def notify_all_waiters(sync):
    if sync:
        sync.set()

    return True

def singleton(class_name):
    """
    Decorator clas
    """
    created_class_objects = {}

    def get_instance(*args, **kwargs):
        """
        create singleton classes based on the args
        """
        key = (class_name, args, str(kwargs))
        if key not in created_class_objects:
            created_class_objects[key] = class_name(*args, **kwargs)
        return created_class_objects[key]

    return get_instance


def execute_the_command(command, pattern=None):

    LOG.info("Executing the command %s", str(command))

    proc = subprocess.Popen(command,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                            )

    stdout = proc.communicate()[0]

    if pattern:
        match_found = re.search(pattern, stdout)
        if match_found:
            return True

    return stdout

def set_execution_completed(finish_execution):
    if finish_execution:
        finish_execution.set()

    return True

def is_execution_completed(finish_execution):
    if finish_execution:
        return finish_execution.is_set()


def ssh_and_execute_command(ip, username, password, command, timeout=10,
                            pkey=None, key_filename=None):

    node_ssh = SSH(username, ip, password=password,
                   pkey=pkey, key_filename=key_filename)
    try:
        code, out, err = node_ssh.execute(command, timeout=timeout)
        if out:
            LOG.debug("Executed the command %s", str(command))
        elif err:
            LOG.error("Error while executing the command %s on node %s ",
                      err, ip)
        return (code, out, err)
    except Exception as exp:
        LOG.warning("Exception when trying to SSH in to node %s ", ip)

        return None, None, None


def ping_ip_address(host, should_succeed=True):
    cmd = ['ping', '-c1', host]
    LOG.debug("Pinging the node %s with cmd = %s", host, cmd)
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    proc.wait()

    return (proc.returncode == 0) == should_succeed


def wait_for_ping(node, timeout, check_interval):
    LOG.debug("Waiting for the ping to succeed timeout = %i interval = %i ",
              timeout, check_interval)
    start = time.time()
    while True:
        if ping_ip_address(node):
            LOG.debug("Ping to %s is Success ", node)
            return True
        time.sleep(check_interval)
        if time.time() - start > timeout:
            LOG.critical("Timeout Exceeded for Ping %s", node)
            break
    return


def infra_assert(evaluate, assert_message):

    try:
        assert evaluate
    except AssertionError:
        LOG.critical(assert_message)

    return

def get_plugin_name(self):
    if self:
        return  str(self).split('plugins.')[1].split('.')[0]

def get_my_pipe_path(self):

    path = get_plugin_name(self)
    node = self.get_input_arguments().keys()[0]

    pipe_path = "/tmp/ha_infra/" + path + "/" + node
    if not os.path.exists(pipe_path):
        LOG.critical("Path doesnt exist for %s", pipe_path)
        os.mkfifo(pipe_path)

    return pipe_path


def clear_ther_terminal(self):
    pipe_path = get_my_pipe_path(self)


def display_on_terminal(self, *kwargs):
    """
    Method to display inforamtion on the xterm
    :param kwargs: message to be displayed
    """
    color = None

    pipe_path = get_my_pipe_path(self)
    with open(pipe_path, "w") as p:
        mobj = re.match(r'color=(\w+)', kwargs[-1])
        if mobj:
            color = str(mobj.group(1).strip())
            data = str("".join(kwargs[:-1]))
        else:
            data = str("".join(kwargs))

        if data.endswith("\n") is False:
            data += "\n"

        if color is not None:
            data = stringc(data, color)

        output = get_plugin_name(self) + " :: " + data
        p.write(output)

def get_openstack_config():
    """
    Method to get the complete openstack config
    :return: dict
    """
    return ha_parser.HAParser().openstack_config

def follow(thefile):
    thefile.seek(0, 2)
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line


@singleton
class HAinfra(object):

    proceed_dict = {}

    def get_proceed_status(self, obj):
        if self.proceed_dict.get(obj, None):
            print "Proceeding :) :) :)"
        else:
            print "DO NOT PROCEED XXXXXXX"

    def set_proceed_status(self, obj):
        self.proceed_dict[obj] = True


if __name__ == "__main__":
    self = "disruptors.plugins.disruptor.Disruptor"
    rows1 = [
        ['a', '1', '2'],
        ['a', '1', '2'],
        ['a', '1', '2']
    ]

    create_report_table(self, "testing")
    add_table_headers(self, "testing", ['A', 'B', 'C'])
    add_table_rows(self, "testing", rows1)

    create_report_table(self, "testing2")
    add_table_headers(self, "testing2", ['A2', 'B2', 'C2'])
    add_table_rows(self, "testing2", rows1)

    self = "runners.plugins.runners.runners"
    rows1 = [
        ['a', '1', '2'],
        ['a', '1', '2'],
        ['a', '1', '2']
    ]

    create_report_table(self, "testing")
    add_table_headers(self, "testing", ['A', 'B', 'C'])
    add_table_rows(self, "testing", rows1)

    create_report_table(self, "testing2")
    add_table_headers(self, "testing2", ['A2', 'B2', 'C2'])
    add_table_rows(self, "testing2", rows1)

    display_infra_report()
