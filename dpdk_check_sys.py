#! /usr/bin/env python
#coding=utf-8
##############################################
# Copyright (c) 2021
# ADVA Optical Networking
# This is the DPDK readyness checklist
#  
##############################################
import os


def read_sys_info(fn):
    try:
        with open(fn, "r") as f:
            s = f.read().rstrip()
    except:
        s = ""
    return s


def check_cpu_freq():
    cur_freq = read_sys_info('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_cur_freq')
    max_freq = read_sys_info('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq')

    if not cur_freq:
        s = os.popen('dmidecode -t 4').read().split('\t')
        for z in s:
            if 'Max Speed' in z:
                max_freq = z.split(':')[1].split()[0]
            elif 'Current Speed:' in z:
                cur_freq = z.split(':')[1].split()[0]

    if (not cur_freq) or (not max_freq):
        print "[error] Can't read CPU frequency "
        return

    cur_freq = int(cur_freq)
    max_freq = int(max_freq)

    if cur_freq < max_freq:
        print "[warning] CPU frequency %d is less than max %d" % (cur_freq, max_freq)
    else:
        print "[OK] CPU frequency is max (%d MHz)" % (max_freq)

def check_cpu_scaling_governor():
    x = read_sys_info('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor')
    if not x: 
        x = '?'

    if x != 'performance':
        print "[error] CPU scaling is %s" % x
    else:
        print "[OK] CPU scaling is %s" % x

def check_swap_enabled():
    fn = '/etc/fstab'

    with open(fn,'r') as f:
        for line in f:
            if not line.startswith('#'):
                if 'swap' in line:
                    print "[error] swap is enabled in %s" % fn
                    return True
        
    print "[OK] swap is disabled"
    return False

def check_huge_pages():
    s = read_sys_info('/proc/meminfo').split('\n')
    n = 0
    sz = 0
    for x in s:
        if 'HugePages_Total' in x:
            a = x.split()
            n = int(a[1])
        if 'Hugepagesize' in x:
            a = x.split()
            sz = int(a[1])
               
    if n>0:
        print "[OK] HugePages_Total: %d, %d kB each" % (n, sz)
    else:
        print "[error] HugePages_Total: %d" % n

def check_irq_balance():
    stat = os.system('systemctl status irqbalance >/dev/null 2>&1')
    if stat != 0:
        print "[OK] irqbalance not active"
    else:
        print \
"""
[error] - please deactivate irqbalance:
\tsystemctl stop irqbalance
\tsystemctl disable irqbalance
"""

#
# nohz_full - Reducing Scheduling-Clock Ticks
# rcu_nocbs - lowering the number of interrupts for the specified cores
#
def check_isol_cpu_cores():
    parms = ('isolcpu','nohz_full','rcu_nocbs')
    vals=["0","0","0"]
    i=0
    s = read_sys_info('/proc/cmdline').split()
    for x in s:
        for y in parms:
            if y in x:
                a = x.split('=')
                print "[OK] %s" % a
                vals[i]=a[1]
                i = i+1

    # print vals
    missed_parms = False
    for index, item in enumerate(vals):
        if item == "0":
            print "[error] - please specify %s ?" % parms[index]
            missed_parms = True

    if missed_parms:
        return

    result = all(element == vals[0] for element in vals)
    if not result:
        print "[error] %s not %s not %s" % (vals[0], vals[1], vals[2])


def check_pstate():
    s = read_sys_info('/proc/cmdline').split()
    for x in s:
        if 'pstate' in x:
            a=x.split('=')
            if a[1] == 'disable':
                print "[OK]", a
            else:
                print "[error] ", x
            return
    
    print "[error] - please add intel_pstate=disable to cmdline"



if __name__ == "__main__":

    print
    msg = "# Checking DPDK system readyness"
    print msg
    print "="*len(msg)
    check_swap_enabled()
    check_huge_pages()
    check_irq_balance()
    check_isol_cpu_cores()
    check_pstate()
    check_cpu_scaling_governor()
    check_cpu_freq()

