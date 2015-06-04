# Nagios CFG generator 
# Gets IP address as argurment and generates cfg files (nagios_host.cfg, nagios_service.cfg )

# From a data template for host and service
# gets the input 
# do duplicate check
# genereate cfg based in input


import os
import sys,re

# ================================= Template part ==============================
# nagios_host Template
nagios_host = """
define host {
	address                        %s
	host_name                      %s
	use                            linux-server
}
"""

# nagios_service Template
nagios_service = """
define service {
	check_command	%s
	host_name	%s
	name	%s
	normal_check_interval	1
	service_description	%s
	use	generic-service
	}"""

HEADER = \
"""# HEADER: This file was autogenerated
# HEADER: by nagios_cfg_gen.  While it can still be managed manually, it
# HEADER: is definitely not recommended."""

# =============================== Template part Ends here ==========================

class NagiosConfigGenUtil(object):

	@staticmethod
	def generate_nagios_appvm_config(ipaddress,host_name,role):
		check_commands = [('check-vm-external-http','HTTP External','t'),\
							('check-vm-external-ssh','SSH External','t'),\
							('check-vm-storage-access','Storage Check','t'),\
							('check_ssh','SSH to VM','f'),\
							('check_ping!100.0,20%!500.0,60%','PING','f')]

		#file_path = os.getcwd() + os.sep + 'nagios_vm_host.cfg'
		#serviceCfgFile = os.getcwd() + os.sep + 'nagios_vm_service.cfg'
		file_path = '/tmp/nagios_install/config/nagios_vm_host.cfg'
		serviceCfgFile = '/tmp/nagios_install/config/nagios_vm_service.cfg'

		if not os.path.isfile(file_path):
			#create nagios_host.cfg
			f = open(file_path,'w+')
			f.write(HEADER)
			f.close()
		if not os.path.isfile(serviceCfgFile):
			sf = open(serviceCfgFile,'w+')
			sf.close()

		f = open(file_path,'a+')
		sf = open(serviceCfgFile,'a+')
		ip_list = NagiosConfigGenUtil.duplicate_check([ipaddress],file_path)
		if ipaddress not in ip_list:
			f.write(nagios_host%(ipaddress,host_name))
			#for check_command in check_commands:
			NagiosConfigGenUtil.writeToServiceFile(check_commands,host_name,sf)

	@staticmethod
	def generate_nagios_host_config(ipaddress,host_name,role):
		"""
		controller_nag_cmds = [('swift-list','Swift List','t'),\
				 ('glance-registry','Glance Registry Service','t'),\
				 ('glance-api','Glance API Service','t'),\
				 ('nova-list','Nova Service List','t'),\
				 ('neutron-service-list','Neutron Service List','t'),\
				 ('neutron-net-list','Neutron Network List','t'),\
				 ('check_ping!100.0,20%!500.0,60%','PING','f')]
		"""
		controller_nag_cmds = [('check_ping!100.0,20%!500.0,60%','PING','f'),\
								('check_ssh','SSH','f')]
		network_nag_cmds = [('check_ping!100.0,20%!500.0,60%','PING','f'),\
								('check_ssh','SSH','f')]
		compute_nag_cmds = [('check_ping!100.0,20%!500.0,60%','PING','f'),\
								('check_ssh','SSH','f')]

		#file_path = os.getcwd() + os.sep + 'nagios_host.cfg'
		#serviceCfgFile = os.getcwd() + os.sep + 'nagios_service.cfg'
		file_path =  '/tmp/nagios_install/config/nagios_host.cfg'
		serviceCfgFile =  '/tmp/nagios_install/config/nagios_service.cfg'
		if not os.path.isfile(file_path):
			#create nagios_host.cfg
			f = open(file_path,'w+')
			f.write(HEADER)
			f.close()
		f = open(file_path,'a+')
		if not os.path.isfile(serviceCfgFile):
			sf = open(serviceCfgFile,'w+')
			sf.close()

		sf = open(serviceCfgFile,'a+')
		ip_list = NagiosConfigGenUtil.duplicate_check([ipaddress],file_path)
		if ipaddress not in ip_list:
			f.write(nagios_host%(ipaddress,host_name))
			if role == "controller":
				NagiosConfigGenUtil.writeToServiceFile(controller_nag_cmds,host_name,sf)
			elif role == "network":
				NagiosConfigGenUtil.writeToServiceFile(network_nag_cmds,host_name,sf)
			elif role == "compute":
				NagiosConfigGenUtil.writeToServiceFile(compute_nag_cmds,host_name,sf)
		f.close()
		sf.close()


	@staticmethod
	def duplicate_check(obj,file_name):
		final_list = []
		#file_path = os.getcwd() + os.sep + file_name
		lines = open(file_name,'r').readlines()
		for line in lines:
			# print re.search(r'1.1.1.1',line)
			for searchitem in obj:
				if re.search(searchitem,line):
					# print line
					final_list.append(searchitem)
		return final_list

	@staticmethod
	def writeToServiceFile(check_commands,host_name,sf):
		for check_command in check_commands:
			if check_command[2] == 't':
				sf.write(nagios_service%('check_nrpe!'+check_command[0],
					 host_name,
					 host_name+"-"+check_command[0],check_command[1]))
			else:
				sf.write(nagios_service%(check_command[0],host_name,
					 host_name+"-"+check_command[0],check_command[1]))
		
if __name__ == "__main__":
	
	# option = raw_input("Enter the CFG option [ 1:nagios_host.cfg | 2:nagios_service.cfg ] - ")
	# if int(option) == 1:
	inputs = sys.argv[1:]
	if inputs[0] == 'ip':
		args = inputs[1].split(',')
	
	elif inputs[0] == 'file':
		# print inputs[0]
		try:
			f = open(inputs[1],'r+')
		except IOError as e:
			print "Error while opening the file %s...%s" % (e)
			args = f.read().splitlines()

	ip_list = []
	if os.path.isfile('nagios_host.cfg'):
		ip_list = duplicate_check(args,'nagios_host.cfg')
		# print ip_list

	for ip in args:
		if ip not in ip_list:
			# print ip
			generate_nagios_host(ip,ip)

	# if int(option) == 2:
	# args = sys.argv[1:]
	# print args
	ip_list = []
	if os.path.isfile('nagios_service.cfg'):
		ip_list = duplicate_check(args,'nagios_service.cfg')
		# print ip_list

	for ip in args:
		if ip not in ip_list:
			# print ip
			generate_nagios_service(ip)
