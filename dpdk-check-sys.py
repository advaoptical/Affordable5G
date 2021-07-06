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
        x = os.popen('tuned-adm active').read().split(':')[1]
    if not x:
        x = '?'

    if 'performance' in x:
        print "[OK] CPU scaling is %s" % x
    else:
        print "[error] CPU scaling is %s" % x
        print "\t please do: tuned-adm profile latency-performance"


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

def check_transparent_huge_pages():
    # Based on the 3.10 kernel operating system, the transparent huge page function 
    # (THP) is turned on by default. THP will cause the operating system 
    # to see that there are large pages and allocate large pages.
    # When large pages cannot be allocated, traditional 4KB pages are allocated.
    # The setting returned in brackets is your current setting
    # To disable THP:
    # echo never > /sys/kernel/mm/transparent_hugepage/enabled
    err_msg = 'error'
    x = '?'
    s = read_sys_info('/sys/kernel/mm/transparent_hugepage/enabled').split()

    if s:
        for x in s:
            if '[' in x:
                if x == '[never]':
                    err_msg = 'OK'
                break
                
    print "[%s] transparent_hugepage/enabled: %s" % (err_msg, x)

    if err_msg != 'OK':
        print "\t - please add transparent_hugepage=never to cmdline"

def check_service(service):
    stat = os.system('systemctl status '+service+' >/dev/null 2>&1')
    if stat != 0:
        print '[OK] '+service+' not active'
    else:
        print "[error] - please deactivate %s:\
        \n\tsystemctl stop %s \n\tsystemctl disable %s" % (service,service,service)

#
# isolcpus
# • Remove cores from the general kernel SMP balancing and scheduler algorithms
# rcu_nocbs
# • prevents Read-Copy-Update (RCU) callback routines from being executed on the targeted cores
# nohz_full
# • Disables kernel timer tick interrupt. Triggered at a periodic interval to keep track of kernel statistics such as CPU and
# memory usage
# https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux_for_real_time/7/html/tuning_guide/offloading_rcu_callbacks
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

# 
# Disables clocksource stability check interrupt for the Time Stamp Counter on all cores
def check_tsc():
    cfg = 'tsc=reliable'
    s = read_sys_info('/proc/cmdline').split()
    for x in s:
        if cfg in x:
            print "[OK]", cfg
            return
    
    print "[error] - please add %s to cmdline" % cfg


# Depending on your system, you'll find it in any one of these:
# /proc/config.gz
# /boot/config
# /boot/config-$(uname -r)
def check_linux_config(cfg):
    paths = ('/proc/config.gz','/boot/config-'+os.uname()[2]) #,'/boot/config'

    for fn in paths:
        if os.path.exists(fn) :
            if '.gz' in fn:
                s = os.popen('cat '+ fn +' | gunzip 2>/dev/null').read()
            else:
                s = os.popen('cat '+ fn).read()

            if cfg in s:
                print "[OK]", cfg
                return

    print "[error] - %s not found" % cfg

def check_hyperthreading():
    s = os.popen('lscpu').read().split('\n')
    n = 1
    for x in s:
        if 'Thread(s) per core' in x:
            n = int(x.split(':')[1])
            break

    if n>1:
        print "[warning] - HT enabled"
    else:
        print "[OK] HT disabled"

if __name__ == "__main__":

    print
    msg = "# Checking DPDK system readyness, kernel: "+os.uname()[2]
    print msg
    print "="*len(msg)
    check_hyperthreading()
    check_swap_enabled()
    check_huge_pages()
    check_isol_cpu_cores()
    check_pstate()
    check_tsc()
    check_cpu_scaling_governor()
    check_cpu_freq()
    check_transparent_huge_pages()
    check_linux_config('CONFIG_NO_HZ_FULL=y')
    check_service('irqbalance')
    check_service('impi')
